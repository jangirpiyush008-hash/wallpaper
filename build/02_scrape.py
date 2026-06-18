"""Scrape article body + images + category from each URL in articles.json."""
import json, re, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
ARTICLES = ROOT / "data" / "articles.json"
OUT = ROOT / "data" / "articles_full.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
TIMEOUT = 20
WORKERS = 20

articles = json.loads(ARTICLES.read_text())
print(f"Scraping {len(articles)} articles with {WORKERS} workers...")

# Resume support
existing = {}
if OUT.exists():
    for a in json.loads(OUT.read_text()):
        existing[a["slug"]] = a
    print(f"Resuming: {len(existing)} already scraped")

def clean_content(soup_content):
    """Strip scripts, Instagram embeds (keep as link), iframes, ads."""
    if not soup_content:
        return "", []
    # Remove script/style
    for tag in soup_content.find_all(["script", "style", "ins", "iframe"]):
        tag.decompose()
    # Convert Instagram blockquote embeds to a simple link
    for bq in soup_content.find_all("blockquote", class_="instagram-media"):
        link = bq.get("data-instgrm-permalink") or ""
        if link:
            a = soup_content.new_tag("a", href=link, target="_blank", rel="noopener")
            a.string = "View on Instagram →"
            p = soup_content.new_tag("p")
            p["class"] = "embed-link"
            p.append(a)
            bq.replace_with(p)
        else:
            bq.decompose()
    # Remove ad containers
    for tag in soup_content.select("[id*=ads], [class*=adsbygoogle], [class*=td-a-rec]"):
        tag.decompose()
    # Collect image URLs
    imgs = []
    for img in soup_content.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if src and src.startswith("http"):
            imgs.append(src)
            img["src"] = src
            # Strip lazy classes/attrs
            for attr in ("data-src", "data-lazy-src", "srcset", "data-srcset", "loading"):
                if attr in img.attrs:
                    del img.attrs[attr]
    return str(soup_content), imgs

def scrape(article):
    url = article["source_url"]
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return {**article, "error": f"http{r.status_code}", "category": "uncategorized", "body_html": "", "body_imgs": []}
        soup = BeautifulSoup(r.text, "lxml")
        cat_el = soup.select_one(".td-post-category")
        category = cat_el.get_text(strip=True).lower() if cat_el else "uncategorized"
        content = soup.select_one(".td-post-content")
        body_html, imgs = clean_content(content)
        return {**article, "category": category, "body_html": body_html, "body_imgs": imgs}
    except Exception as e:
        return {**article, "error": str(e)[:100], "category": "uncategorized", "body_html": "", "body_imgs": []}

results = list(existing.values())
todo = [a for a in articles if a["slug"] not in existing]
print(f"Remaining: {len(todo)}")

done = 0
last_save = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futures = {ex.submit(scrape, a): a for a in todo}
    for f in as_completed(futures):
        res = f.result()
        results.append(res)
        done += 1
        if done % 20 == 0 or done == len(todo):
            print(f"  {done}/{len(todo)}  [{res['slug'][:40]}] cat={res.get('category')} err={res.get('error','-')}")
        # Periodic checkpoint
        if time.time() - last_save > 30:
            OUT.write_text(json.dumps(results, ensure_ascii=False))
            last_save = time.time()

OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False))
errs = sum(1 for r in results if r.get("error"))
print(f"\nDone. Total: {len(results)}, errors: {errs}")
print(f"Categories: {set(r.get('category') for r in results)}")
