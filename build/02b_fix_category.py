"""Re-fetch each article URL just to grab the correct category (a[href*=/category/])."""
import json, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
SRC = ROOT / "data" / "articles_full.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

arts = json.loads(SRC.read_text())

def get_cat(a):
    try:
        r = requests.get(a["source_url"], headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        # The article's own category: link in post header area, not sidebar
        # Try .td-category first (under post title)
        el = soup.select_one(".td-category a, .entry-category a")
        if el and el.get("href") and "/category/" in el.get("href"):
            return el.get_text(strip=True).lower()
        # Fallback: any category link near the title
        for link in soup.select('a[href*="/category/"]'):
            # Ignore those inside related-posts sidebar
            parents = [p.get("class") or [] for p in link.parents][:5]
            if any("td-module-image" in (c if isinstance(c, list) else []) for c in parents):
                continue
            href = link.get("href", "")
            m = re.search(r"/category/([^/]+)/", href)
            if m:
                return m.group(1).replace("-", " ")
        return "uncategorized"
    except Exception:
        return a.get("category", "uncategorized")

with ThreadPoolExecutor(max_workers=25) as ex:
    futures = {ex.submit(get_cat, a): a for a in arts}
    done = 0
    for f in as_completed(futures):
        a = futures[f]
        a["category"] = f.result()
        done += 1
        if done % 100 == 0:
            print(f"  {done}/{len(arts)}")

SRC.write_text(json.dumps(arts, indent=2, ensure_ascii=False))
from collections import Counter
print("Category distribution:", Counter(a["category"] for a in arts).most_common(20))
