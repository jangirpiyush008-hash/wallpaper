"""Generate full static site: homepage(s), category pages, article pages, about, privacy."""
import json, html, random, re
from pathlib import Path
from collections import defaultdict
from html import escape

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "articles_full.json"
arts = json.loads(DATA.read_text())

# Sort by date (newest first). Date format "April 28, 2025"
from datetime import datetime
def parse_date(s):
    try:
        return datetime.strptime(s, "%B %d, %Y")
    except Exception:
        return datetime(1970, 1, 1)
arts.sort(key=lambda a: parse_date(a.get("date", "")), reverse=True)

# Main nav categories (as per screenshot)
NAV_CATS = [("animals", "Animals"), ("art", "Art"), ("food & drinks", "Food & Drinks"), ("illustrations", "Illustrations")]
NAV_SLUGS = {k: v for k, v in NAV_CATS}

def cat_slug(c):
    return c.replace(" & ", "-").replace(" ", "-").lower()

# Group by category
by_cat = defaultdict(list)
for a in arts:
    by_cat[a["category"]].append(a)

# ---------------- Templates ----------------
def header(active=""):
    nav_items = '<a href="index.html"' + (' class="active"' if active == "home" else "") + '>Home</a>'
    for c, label in NAV_CATS:
        slug = cat_slug(c)
        cls = ' class="active"' if active == c else ""
        nav_items += f'<a href="category-{slug}.html"{cls}>{label}</a>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{{title}}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Open+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
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

def card_html(a):
    img = a.get("thumb_local") or a.get("hero_local") or ""
    return f"""<a class="card" href="article-{a['slug']}.html">
  <img class="card-img" src="{img}" alt="{escape(a['title'])}" loading="lazy">
  <div class="card-title">{escape(a['title'])}</div>
</a>"""

def pagination_html(current, total, prefix):
    if total <= 1: return ""
    parts = []
    def link(p, label=None, cur=False, dots=False):
        if dots: return '<span class="dots">…</span>'
        if cur: return f'<span class="current">{label or p}</span>'
        href = f'{prefix}.html' if p == 1 else f'{prefix}-{p}.html'
        return f'<a href="{href}">{label or p}</a>'
    if current > 1: parts.append(link(current - 1, "« Prev"))
    # window
    window = set([1, total, current - 1, current, current + 1])
    last = 0
    for p in sorted(window):
        if p < 1 or p > total: continue
        if p - last > 1: parts.append(link(0, dots=True))
        parts.append(link(p, cur=(p == current)))
        last = p
    if current < total: parts.append(link(current + 1, "Next »"))
    return f'<div class="pagination">{"".join(parts)}</div>'

# ---------------- HOMEPAGE (paginated) ----------------
PER_PAGE = 30
def render_home_pages():
    total = (len(arts) + PER_PAGE - 1) // PER_PAGE
    for page in range(1, total + 1):
        chunk = arts[(page-1)*PER_PAGE : page*PER_PAGE]
        cards = "\n".join(card_html(a) for a in chunk)
        body = f"""<div class="home-wrap">
  <div class="home-grid">{cards}</div>
</div>
{pagination_html(page, total, "index")}
"""
        out = "index.html" if page == 1 else f"index-{page}.html"
        title = "Wallpaper Data" + (f" — Page {page}" if page > 1 else "")
        html_str = header("home").replace("{title}", title) + body + FOOTER
        (ROOT / out).write_text(html_str, encoding="utf-8")
    print(f"Homepage: {total} pages")

# ---------------- CATEGORY PAGES ----------------
def render_category_pages():
    # Main category pages
    for cat, label in NAV_CATS:
        items = by_cat.get(cat, [])
        slug = cat_slug(cat)
        total = max(1, (len(items) + PER_PAGE - 1) // PER_PAGE)
        for page in range(1, total + 1):
            chunk = items[(page-1)*PER_PAGE : page*PER_PAGE]
            cards = "\n".join(card_html(a) for a in chunk) if chunk else "<p>No articles yet.</p>"
            body = f"""<div class="cat-header"><h1>{escape(label.lower())}</h1></div>
<div class="home-wrap">
  <div class="home-grid">{cards}</div>
</div>
{pagination_html(page, total, f"category-{slug}")}
"""
            out = f"category-{slug}.html" if page == 1 else f"category-{slug}-{page}.html"
            title = f"{label} — Wallpaper Data" + (f" — Page {page}" if page > 1 else "")
            html_str = header(cat).replace("{title}", title) + body + FOOTER
            (ROOT / out).write_text(html_str, encoding="utf-8")
        print(f"Category '{cat}': {len(items)} articles, {total} page(s)")

# ---------------- ARTICLE PAGES ----------------
def sidebar_html(current_slug):
    """Pick 5 random articles for the 'CHECK THIS OUT' sidebar."""
    pool = [a for a in arts if a["slug"] != current_slug]
    picks = random.sample(pool, min(5, len(pool)))
    html_parts = ['<div class="sidebar"><div class="sidebar-title">CHECK THIS OUT</div>']
    for p in picks:
        img = p.get("thumb_local") or p.get("hero_local") or ""
        cat = p.get("category", "")
        html_parts.append(f"""<div class="side-card">
  <a href="article-{p['slug']}.html" class="img-wrap">
    <img src="{img}" alt="{escape(p['title'])}" loading="lazy">
    <span class="cat-badge">{escape(cat)}</span>
  </a>
  <a href="article-{p['slug']}.html" class="s-title">{escape(p['title'])}</a>
  <div class="s-meta"><a href="author-{p['author_slug']}.html">{escape(p['author'])}</a> &nbsp;-&nbsp; {escape(p['date'])}</div>
</div>""")
    html_parts.append("</div>")
    return "\n".join(html_parts)

def render_articles():
    for i, a in enumerate(arts):
        prev_a = arts[i - 1] if i > 0 else None
        next_a = arts[i + 1] if i < len(arts) - 1 else None
        # Choose active nav
        active = a["category"] if a["category"] in NAV_SLUGS else ""
        hero = a.get("hero_local") or a.get("thumb_local") or ""
        body_html = a.get("body_html") or f"<p>{escape(a['title'])}</p>"
        # Remove the wrapping div class if present (we provide our own .post-content wrapper)
        body_html = re.sub(r'^\s*<div class="td-post-content[^"]*"[^>]*>', '', body_html)
        body_html = re.sub(r'</div>\s*$', '', body_html)

        prev_html = ""
        if prev_a:
            prev_html = f'<div class="col prev"><span class="label">Previous article</span><a href="article-{prev_a["slug"]}.html">{escape(prev_a["title"])}</a></div>'
        else:
            prev_html = '<div class="col prev"></div>'
        next_html = ""
        if next_a:
            next_html = f'<div class="col next"><span class="label">Next article</span><a href="article-{next_a["slug"]}.html">{escape(next_a["title"])}</a></div>'
        else:
            next_html = '<div class="col next"></div>'

        article_body = f"""<div class="article-wrap">
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
        html_str = header(active).replace("{title}", f"{a['title']} — Wallpaper Data") + article_body + FOOTER
        (ROOT / f"article-{a['slug']}.html").write_text(html_str, encoding="utf-8")
        if (i + 1) % 200 == 0:
            print(f"  articles: {i+1}/{len(arts)}")
    print(f"Articles: {len(arts)} pages")

# ---------------- AUTHOR PAGES ----------------
def render_authors():
    by_author = defaultdict(list)
    for a in arts:
        by_author[a["author_slug"]].append(a)
    for slug, items in by_author.items():
        cards = "\n".join(card_html(a) for a in items)
        body = f"""<div class="cat-header"><h1>By {escape(items[0]['author'])}</h1></div>
<div class="home-wrap"><div class="home-grid">{cards}</div></div>
"""
        title = f"{items[0]['author']} — Wallpaper Data"
        html_str = header().replace("{title}", title) + body + FOOTER
        (ROOT / f"author-{slug}.html").write_text(html_str, encoding="utf-8")
    print(f"Authors: {len(by_author)} pages")

# ---------------- STATIC PAGES ----------------
def render_static():
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
    (ROOT / "about.html").write_text(header().replace("{title}", "About Us — Wallpaper Data") + about + FOOTER, encoding="utf-8")
    (ROOT / "privacy.html").write_text(header().replace("{title}", "Privacy Policy — Wallpaper Data") + privacy + FOOTER, encoding="utf-8")
    print("Static: about.html, privacy.html")

# Run
random.seed(42)
render_home_pages()
render_category_pages()
render_articles()
render_authors()
render_static()
print(f"\nTotal pages generated.")
import subprocess
print(subprocess.check_output(["bash", "-c", f"ls '{ROOT}' | wc -l"]).decode().strip(), "files in root")
