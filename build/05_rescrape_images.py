"""Re-fetch article pages and extract ALL images (including lazy-loaded, galleries, etc)."""
import json, re, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "articles_full.json"
arts = json.loads(DATA.read_text())

HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 20
WORKERS = 15

def get_all_images(url):
    """Extract ALL image URLs from an article page."""
    imgs = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return imgs
        soup = BeautifulSoup(r.text, "html.parser")
        content = soup.select_one(".td-post-content")
        if not content:
            return imgs

        # Find all img tags
        for img in content.find_all("img"):
            for attr in ("src", "data-src", "data-lazy-src", "data-srcset"):
                src = img.get(attr)
                if src and src.startswith("http"):
                    # Extract base URL from srcset if needed
                    if attr.endswith("srcset"):
                        src = src.split()[0]
                    if src not in imgs:
                        imgs.append(src)

        # Find images in picture/source tags
        for pic in content.find_all("picture"):
            for src in pic.find_all("source"):
                srcset = src.get("srcset")
                if srcset:
                    url_part = srcset.split()[0]
                    if url_part.startswith("http") and url_part not in imgs:
                        imgs.append(url_part)
            # fallback img in picture
            fallback = pic.find("img")
            if fallback:
                for attr in ("src", "data-src"):
                    s = fallback.get(attr)
                    if s and s.startswith("http") and s not in imgs:
                        imgs.append(s)

        # Strip query params and thumbnails, keep only real images
        clean_imgs = []
        for img_url in imgs:
            # Skip tiny thumbnails (324x235 pattern)
            if re.search(r'-\d{2,3}x\d{2,3}\.', img_url):
                img_url = re.sub(r'-\d+x\d+(\.\w+)$', r'\1', img_url)
            if img_url not in clean_imgs:
                clean_imgs.append(img_url)
        return clean_imgs[:10]  # cap at 10 per article
    except Exception as e:
        return imgs

print(f"Re-scraping {len(arts)} articles for images...")
done = 0
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futures = {ex.submit(get_all_images, a["source_url"]): a for a in arts}
    for f in as_completed(futures):
        a = futures[f]
        new_imgs = f.result()
        # Append to body_imgs, keep hero and thumb
        a["body_imgs"] = list(dict.fromkeys([a.get("hero_local") or a.get("hero_url") or ""] + (new_imgs or [])))
        a["body_imgs"] = [u for u in a["body_imgs"] if u]  # remove empties
        done += 1
        if done % 100 == 0:
            print(f"  {done}/{len(arts)}")

# Count images per article
img_counts = {}
for cnt in range(1, 11):
    img_counts[cnt] = sum(1 for a in arts if len(a.get("body_imgs", [])) == cnt)

DATA.write_text(json.dumps(arts, indent=2, ensure_ascii=False))
print(f"\nImage distribution:")
for cnt in sorted(img_counts.keys()):
    if img_counts[cnt] > 0:
        print(f"  {cnt} images: {img_counts[cnt]} articles")
avg = sum(len(a.get("body_imgs", [])) for a in arts) / len(arts)
print(f"Average images per article: {avg:.1f}")
