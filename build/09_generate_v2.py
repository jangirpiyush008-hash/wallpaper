"""
v2 generator:
 - Homepage: ONE page, infinite-scroll JS appends cards.
 - Category pages: ONE page each, infinite-scroll JS.
 - Article pages: use final_body_html with spliced images, no Instagram, prev/next, author card.
 - Author + About + Privacy as before.
 - Strip old paginated index-2.html, category-X-2.html files.
"""
import json, html, random, re
from pathlib import Path
from collections import defaultdict
from html import escape
from datetime import datetime

ROOT = Path("/Users/piyushjangir/Documents/Ankush Website/Newspaper")
DATA = ROOT / "data" / "articles_full.json"
arts = json.loads(DATA.read_text())

def parse_date(s):
    try:
        return datetime.strptime(s, "%B %d, %Y")
    except Exception:
        return datetime(1970, 1, 1)
arts.sort(key=lambda a: parse_date(a.get("date", "")), reverse=True)

NAV_CATS = [("animals", "Animals"), ("art", "Art"), ("food & drinks", "Food & Drinks"), ("illustrations", "Illustrations")]
NAV_SLUGS = {k: v for k, v in NAV_CATS}

def cat_slug(c):
    return c.replace(" & ", "-").replace(" ", "-").lower()

by_cat = defaultdict(list)
for a in arts:
    by_cat[a["category"]].append(a)

# Clean up old paginated files
for f in ROOT.glob("index-*.html"):
    f.unlink()
for f in ROOT.glob("category-*-[0-9]*.html"):
    f.unlink()
print("Cleaned old paginated pages.")

def header(active="", title="Wallpaper Data"):
    nav_items = '<a href="index.html"' + (' class="active"' if active == "home" else "") + '>Home</a>'
    for c, label in NAV_CATS:
        slug = cat_slug(c)
        cls = ' class="active"' if active == c else ""
        nav_items += f'<a href="category-{slug}.html"{cls}>{label}</a>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Roboto:wght@400;500;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site-header">
  <div class="header-inner">
    <div class="logo"><a href="index.html">Wallpaper Data</a></div>
    <nav class="main-nav">{nav_items}</nav>
  </div>
</header>
"""

FOOTER = """<footer class="site-footer">
  <div class="footer-inner">
    <div class="footer-col">
      <div class="footer-logo">Wallpaper Data</div>
      <p>A collection of beautiful wallpapers, art, illustrations and stories from around the world.</p>
    </div>
    <div class="footer-col">
      <h4>Categories</h4>
      <a href="category-animals.html">Animals</a>
      <a href="category-art.html">Art</a>
      <a href="category-food-drinks.html">Food &amp; Drinks</a>
      <a href="category-illustrations.html">Illustrations</a>
    </div>
    <div class="footer-col">
      <h4>About</h4>
      <a href="about.html">About Us</a>
      <a href="privacy.html">Privacy Policy</a>
    </div>
  </div>
  <div class="footer-bottom">© Wallpaper Data — All Rights Reserved</div>
</footer>
</body></html>"""

def js_card_array(items):
    arr = []
    for a in items:
        arr.append({
            "s": a["slug"],
            "t": a["title"],
            "i": a.get("thumb_local") or a.get("hero_local") or "",
        })
    return arr

def render_listing_page(items, active, page_title, out_file, header_html=None):
    cards_json = json.dumps(js_card_array(items), ensure_ascii=False)
    head = header_html if header_html else ""
    body = f"""{head}
<div class="home-wrap">
  <div class="home-grid"></div>
  <div class="load-more-wrap">
    <div id="infinite-loader" class="infinite-loader">Loading more…</div>
    <button id="load-more-btn" class="load-more-btn" type="button">Load More</button>
  </div>
</div>
<script>window.__cards = {cards_json};</script>
<script src="assets/infinite.js" defer></script>
"""
    html_str = header(active, page_title) + body + FOOTER
    (ROOT / out_file).write_text(html_str, encoding="utf-8")

# Homepage
render_listing_page(arts, "home", "Wallpaper Data", "index.html")
print(f"Homepage: 1 page with infinite scroll over {len(arts)} cards")

# Category pages
for cat, label in NAV_CATS:
    items = by_cat.get(cat, [])
    slug = cat_slug(cat)
    cat_head = f'<div class="cat-header"><h1>{escape(label.lower())}</h1></div>'
    render_listing_page(items, cat, f"{label} — Wallpaper Data", f"category-{slug}.html", cat_head)
    print(f"  category-{slug}.html: {len(items)} cards")

# Author pages
by_author = defaultdict(list)
for a in arts:
    by_author[a["author_slug"]].append(a)
for slug, items in by_author.items():
    cat_head = f'<div class="cat-header"><h1>By {escape(items[0]["author"])}</h1></div>'
    render_listing_page(items, "", f"{items[0]['author']} — Wallpaper Data", f"author-{slug}.html", cat_head)
print(f"Authors: {len(by_author)} pages")

# Article pages
random.seed(42)
def sidebar_html(current_slug):
    pool = [a for a in arts if a["slug"] != current_slug]
    picks = random.sample(pool, min(5, len(pool)))
    parts = ['<aside class="sidebar"><div class="sidebar-title">CHECK THIS OUT</div>']
    for p in picks:
        img = p.get("thumb_local") or p.get("hero_local") or ""
        cat = p.get("category", "")
        parts.append(f"""<div class="side-card">
  <a href="article-{p['slug']}.html" class="img-wrap">
    <img src="{img}" alt="{escape(p['title'])}" loading="lazy">
    <span class="cat-badge">{escape(cat)}</span>
  </a>
  <a href="article-{p['slug']}.html" class="s-title">{escape(p['title'])}</a>
  <div class="s-meta"><a href="author-{p['author_slug']}.html">{escape(p['author'])}</a> &nbsp;-&nbsp; {escape(p['date'])}</div>
</div>""")
    parts.append("</aside>")
    return "\n".join(parts)

for i, a in enumerate(arts):
    prev_a = arts[i - 1] if i > 0 else None
    next_a = arts[i + 1] if i < len(arts) - 1 else None
    active = a["category"] if a["category"] in NAV_SLUGS else ""
    hero = a.get("hero_local") or a.get("thumb_local") or ""
    body_html = a.get("final_body_html") or f"<p>{escape(a['title'])}</p>"

    prev_html = ('<div class="col prev"><span class="label">Previous article</span>'
                 f'<a href="article-{prev_a["slug"]}.html">{escape(prev_a["title"])}</a></div>'
                 if prev_a else '<div class="col prev"></div>')
    next_html = ('<div class="col next"><span class="label">Next article</span>'
                 f'<a href="article-{next_a["slug"]}.html">{escape(next_a["title"])}</a></div>'
                 if next_a else '<div class="col next"></div>')

    body = f"""<div class="article-wrap">
  <main>
    <h1 class="post-title">{escape(a['title'])}</h1>
    <div class="post-meta">
      <span>By <a href="author-{a['author_slug']}.html">{escape(a['author'])}</a></span>
      <span class="sep">-</span>
      <span>{escape(a['date'])}</span>
    </div>
    <div class="post-hero"><img src="{hero}" alt="{escape(a['title'])}"></div>
    <div class="post-content">{body_html}</div>
    <div class="prev-next">{prev_html}{next_html}</div>
    <div class="author-card">
      <div class="author-avatar">&#128100;</div>
      <div class="author-info"><div class="name">{escape(a['author'])}</div></div>
    </div>
  </main>
  {sidebar_html(a['slug'])}
</div>
"""
    html_str = header(active, f"{a['title']} — Wallpaper Data") + body + FOOTER
    (ROOT / f"article-{a['slug']}.html").write_text(html_str, encoding="utf-8")
    if (i + 1) % 200 == 0:
        print(f"  articles: {i+1}/{len(arts)}")
print(f"Articles: {len(arts)} pages")

# About + Privacy
about = """<div class="static-page">
<h1>About Us</h1>
<p>Welcome to <strong>Wallpaper Data</strong> — a place to discover beautiful wallpapers, art, illustrations and stories from creators around the world.</p>
<p>We curate fresh inspiration daily: hand-picked imagery across animals, art, food &amp; drinks, illustrations, nature, fashion, architecture and much more. Whether you are looking for the perfect background for your desktop, laptop or phone, or simply love discovering new artists, you'll find something here.</p>
<h2>What we do</h2>
<p>Every article is researched and written by our editorial team. We profile artists, surface their work, and share the high-resolution imagery so you can enjoy it on any screen.</p>
<h2>Get in touch</h2>
<p>Have a story or artist you think we should cover? We'd love to hear from you. Reach out through our contact page.</p>
</div>"""
privacy = """<div class="static-page">
<h1>Privacy Policy</h1>
<p>Last updated: 2026</p>
<p>This Privacy Policy describes how Wallpaper Data ("we", "us", or "our") collects, uses, and protects information when you visit our website.</p>
<h2>Information we collect</h2>
<p>We may collect non-personal information such as your browser type, device, pages visited, and the time spent on each page. This information helps us improve the site.</p>
<h2>Cookies</h2>
<p>We use cookies to remember preferences and to power basic analytics. You can disable cookies in your browser settings; some parts of the site may not function as expected without them.</p>
<h2>Third-party services</h2>
<p>We may use third-party analytics or advertising services that collect information through standard logging and cookies in accordance with their own policies.</p>
<h2>Your rights</h2>
<p>You have the right to request access to, correction of, or deletion of any personal information we may hold about you.</p>
<h2>Contact</h2>
<p>If you have questions about this Privacy Policy, please contact us via our website.</p>
</div>"""
(ROOT / "about.html").write_text(header("", "About Us — Wallpaper Data") + about + FOOTER, encoding="utf-8")
(ROOT / "privacy.html").write_text(header("", "Privacy Policy — Wallpaper Data") + privacy + FOOTER, encoding="utf-8")
print("Static: about.html, privacy.html")
