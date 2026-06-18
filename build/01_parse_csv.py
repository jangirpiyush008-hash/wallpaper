"""Parse wallpaperdata.csv, flatten 3-cols-per-row, dedupe, output articles.json."""
import csv, json, re, sys
from pathlib import Path
from urllib.parse import urlparse

CSV_PATH = Path("/Users/piyushjangir/Downloads/wallpaperdata.csv")
OUT = Path(__file__).parent.parent / "data" / "articles.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

def slugify(url):
    p = urlparse(url).path.strip("/")
    return p.split("/")[-1] if p else ""

def upgrade_img(url):
    # Strip "-324x235" thumbnail suffix to get full-size image
    return re.sub(r"-\d+x\d+(\.(?:jpg|jpeg|png|webp|gif))$", r"\1", url, flags=re.I)

articles = []
seen = set()
with CSV_PATH.open(newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    for row in reader:
        # Each row has 3 article tuples of 6 fields = 18 cols
        for i in range(0, min(len(row), 18), 6):
            try:
                url, img, title, author, author_url, date = row[i:i+6]
            except ValueError:
                continue
            url = (url or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            slug = slugify(url)
            if not slug:
                continue
            articles.append({
                "slug": slug,
                "title": (title or "").strip(),
                "author": (author or "").strip() or "Wallpaper Data",
                "author_slug": slugify(author_url) if author_url else "wallpaper-data",
                "date": (date or "").strip(),
                "thumb_url": (img or "").strip(),
                "hero_url": upgrade_img((img or "").strip()),
                "source_url": url,
            })

OUT.write_text(json.dumps(articles, indent=2, ensure_ascii=False))
print(f"Unique articles: {len(articles)}")
print(f"Sample: {articles[0]}")
print(f"Written: {OUT}")
