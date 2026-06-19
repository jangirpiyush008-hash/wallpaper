"""Add a single article (each-of-these-rare-historical-c6) to articles_full.json.
Downloads its hero image and writes a short original body intro.
"""
import json, hashlib, re
from pathlib import Path
from urllib.parse import urlparse
import requests

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "articles_full.json"
IMG_DIR = ROOT / "images"

HERO_URL = "https://img.wallpaperdata.com/articles/5rkYmzOcn9vu1hHgDqA3Jh/usj6jyzd2ijzmaqp.jpg"
TITLE = "Each of These Rare Historical Photos Has a Unique Story to Tell"
AUTHOR = "Abigail P"
DATE = "December 24, 2025"
SOURCE_URL = "https://wallpaperdata.com/each-of-these-rare-historical-c6/"
SLUG = "each-of-these-rare-historical-c6"
CATEGORY = "people"

def local_name(url):
    p = urlparse(url).path
    base = Path(p).name or "img"
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{h}_{base}"

def download(url):
    fname = local_name(url)
    out = IMG_DIR / fname
    if out.exists() and out.stat().st_size > 0:
        return f"images/{fname}"
    r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=30, stream=True)
    if r.status_code != 200:
        print(f"  FAIL {r.status_code}: {url}")
        return url
    with open(out, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    print(f"  saved {fname} ({out.stat().st_size//1024}KB)")
    return f"images/{fname}"

hero_local = download(HERO_URL)

# Original short body
body = """<p>Historical photographs hold a peculiar power — a single frame can preserve a moment that words could never quite capture. The collection gathered here spans decades of fleeting events, candid expressions, and small details from everyday life that history books rarely bother to mention.</p>
<p>Some of these images surface in archives by accident. Others sit in family albums for generations before someone notices their significance. Together they form a quiet record of how people actually lived, dressed, worked, and gathered, far away from the formal portraits that usually define an era.</p>
<p>What makes them rare is not just their age but the stories tucked inside the frame: the half-finished gesture, the background detail, the unidentified face. Each photo invites a closer look and a fresh question about the time it came from.</p>
<figure class="post-inline-img"><img src="{hero}" alt="{title}" loading="lazy"></figure>
<p>Browsing through a set like this is part history lesson, part time travel. The clothes, the architecture, the cars, the streets — every element offers a hook for the imagination. Even the lighting and framing reveal the limits of cameras at the time, which makes the moments that did get captured feel all the more precious.</p>
<p>Take a slow scroll, and let the small details do the storytelling.</p>""".format(hero=hero_local, title=TITLE.replace('"', '&quot;'))

arts = json.loads(DATA.read_text())
# Check if already exists
if any(a["slug"] == SLUG for a in arts):
    print("Already exists; skipping insert.")
else:
    new_article = {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "author_slug": "abigail-p",
        "date": DATE,
        "thumb_url": HERO_URL,
        "hero_url": HERO_URL,
        "source_url": SOURCE_URL,
        "category": CATEGORY,
        "body_html": "",
        "body_imgs": [HERO_URL],
        "thumb_local": hero_local,
        "hero_local": hero_local,
        "body_rewritten": body,
        "final_body_html": body,
        "word_count": len(re.sub(r"<[^>]+>", " ", body).split()),
    }
    # Insert at front (newest)
    arts.insert(0, new_article)
    DATA.write_text(json.dumps(arts, indent=2, ensure_ascii=False))
    print(f"Inserted. Total articles now: {len(arts)}")
