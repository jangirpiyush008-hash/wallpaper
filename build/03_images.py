"""Download all images (hero + body) for every article. Rewrite URLs in body_html to local paths."""
import json, re, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import requests

ROOT = Path(__file__).parent.parent
SRC = ROOT / "data" / "articles_full.json"
IMG_DIR = ROOT / "images"
IMG_DIR.mkdir(exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0"}

arts = json.loads(SRC.read_text())

def local_name(url):
    """Stable filename from URL."""
    p = urlparse(url).path
    base = Path(p).name or "img"
    # Prefix with short hash to avoid collisions
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{h}_{base}"

# Collect every unique image URL
urls = set()
for a in arts:
    if a.get("hero_url"):
        urls.add(a["hero_url"])
    if a.get("thumb_url"):
        urls.add(a["thumb_url"])
    for u in a.get("body_imgs", []) or []:
        urls.add(u)

print(f"Unique image URLs to download: {len(urls)}")

# Build URL -> local filename map
url_to_local = {u: local_name(u) for u in urls}

def fetch(url):
    fname = url_to_local[url]
    out = IMG_DIR / fname
    if out.exists() and out.stat().st_size > 0:
        return url, True, "cached"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20, stream=True)
        if r.status_code != 200:
            # If hero_url failed (we stripped -324x235), try original thumb URL pattern
            return url, False, f"http{r.status_code}"
        with open(out, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return url, True, "ok"
    except Exception as e:
        return url, False, str(e)[:40]

ok = 0
fail = 0
failed_urls = []
with ThreadPoolExecutor(max_workers=30) as ex:
    futs = [ex.submit(fetch, u) for u in urls]
    for i, f in enumerate(as_completed(futs), 1):
        url, success, msg = f.result()
        if success:
            ok += 1
        else:
            fail += 1
            failed_urls.append((url, msg))
        if i % 100 == 0:
            print(f"  {i}/{len(urls)}  ok={ok} fail={fail}")

print(f"\nTotal: ok={ok} fail={fail}")
if failed_urls[:5]:
    print("Sample failures:", failed_urls[:5])

# For failed hero URLs, try falling back to thumb URL
print("\nRetrying failed heroes with thumbnails...")
retry_map = {}  # original_url -> new_url to use
for a in arts:
    h = a.get("hero_url")
    t = a.get("thumb_url")
    if h and h != t and (IMG_DIR / url_to_local[h]).exists() is False:
        # hero failed; ensure thumb is downloaded and use thumb
        retry_map[h] = t

print(f"Heroes to remap to thumb: {len(retry_map)}")

# Rewrite body_html and update hero_url/thumb_url to local paths "images/<fname>"
def to_local(url):
    if not url:
        return url
    if url in url_to_local:
        f = url_to_local[url]
        if (IMG_DIR / f).exists() and (IMG_DIR / f).stat().st_size > 0:
            return f"images/{f}"
    # fallback: keep original (will hotlink)
    return url

for a in arts:
    # hero: if hero file missing, use thumb
    h, t = a.get("hero_url"), a.get("thumb_url")
    hero_local = to_local(h)
    if hero_local == h and t:  # hero didn't resolve locally
        hero_local = to_local(t)
    a["hero_local"] = hero_local
    a["thumb_local"] = to_local(t) if t else hero_local
    # Rewrite body images
    body = a.get("body_html", "") or ""
    for u in a.get("body_imgs", []) or []:
        local = to_local(u)
        if local != u:
            body = body.replace(u, local)
    a["body_html"] = body

SRC.write_text(json.dumps(arts, indent=2, ensure_ascii=False))
print("URLs rewritten in articles_full.json")
