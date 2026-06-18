"""
For each article:
 - Pick body_rewritten if present, else fall back to body_html (the scraped original).
 - Strip Instagram embeds entirely (no 'View on Instagram' link).
 - Convert plain text paragraphs (rewrites have no <p> tags) into <p>...</p>.
 - Splice 3-4 article images between paragraphs at even intervals.
 - Save as final_body_html ready for HTML template.
"""
import json, re, html
from pathlib import Path
from html import escape

ROOT = Path("/Users/piyushjangir/Documents/Ankush Website/Newspaper")
DATA = ROOT / "data" / "articles_full.json"
arts = json.loads(DATA.read_text())

def to_local_image(url):
    """Convert image URL to local path if it was downloaded."""
    if not url:
        return url
    if url.startswith("images/"):
        return url
    # Use a hash lookup against existing images
    import hashlib
    if url.startswith("http"):
        from urllib.parse import urlparse
        h = hashlib.md5(url.encode()).hexdigest()[:8]
        base = Path(urlparse(url).path).name or "img"
        local = ROOT / "images" / f"{h}_{base}"
        if local.exists():
            return f"images/{h}_{base}"
    return url

def paragraphs_from_text(text):
    """Split plain text into paragraphs."""
    # Strip code-block markers if any
    text = re.sub(r"^```\w*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # If body already contains <p> or <div>, treat as HTML
    if re.search(r"<(p|div|h2|h3)[\s>]", text, re.I):
        # Already HTML - just strip blockquotes (Instagram) and ads
        # Remove Instagram embeds
        text = re.sub(r'<blockquote[^>]*class="[^"]*instagram[^"]*"[^>]*>.*?</blockquote>', '', text, flags=re.I | re.S)
        text = re.sub(r'<p[^>]*class="[^"]*embed-link[^"]*"[^>]*>.*?</p>', '', text, flags=re.I | re.S)
        # Remove "View on Instagram" links
        text = re.sub(r'<a[^>]*>View on Instagram[^<]*</a>', '', text, flags=re.I)
        # Extract paragraphs
        paras = re.findall(r'<p[^>]*>(.*?)</p>', text, re.I | re.S)
        if paras:
            return [p.strip() for p in paras if p.strip() and len(p.strip()) > 20]
        # Fall through to plain-text mode
        text = re.sub(r'<[^>]+>', '', text)
    # Plain text: split on double newlines, then single newlines
    parts = re.split(r"\n\s*\n", text.strip())
    parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 20]
    # If only one big block, split on sentence groups
    if len(parts) <= 2 and any(len(p) > 1000 for p in parts):
        new_parts = []
        for p in parts:
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', p)
            # Group every 3-4 sentences into a paragraph
            for i in range(0, len(sentences), 4):
                chunk = " ".join(sentences[i:i+4]).strip()
                if chunk:
                    new_parts.append(chunk)
        parts = new_parts
    return parts

def splice_images(paragraphs, image_urls, title):
    """Insert images between paragraphs at even intervals.
    Skip the first image (already used as hero). Place 3-4 images between paragraphs."""
    if not paragraphs:
        return ""
    # Use images 1..N as body images (image 0 is hero, used outside)
    body_imgs = image_urls[1:] if len(image_urls) > 1 else image_urls[:1]
    body_imgs = [to_local_image(u) for u in body_imgs[:4]]  # max 4
    n_imgs = len(body_imgs)
    n_paras = len(paragraphs)
    if n_imgs == 0 or n_paras < 3:
        return "\n".join(f"<p>{p}</p>" for p in paragraphs)
    # Position images: after paragraph at floor((i+1) * n_paras / (n_imgs+1))
    img_positions = {}
    for i, img in enumerate(body_imgs):
        pos = int((i + 1) * n_paras / (n_imgs + 1))
        pos = max(1, min(pos, n_paras - 1))
        # avoid putting two images at same position
        while pos in img_positions and pos < n_paras - 1:
            pos += 1
        img_positions[pos] = img
    out = []
    for i, p in enumerate(paragraphs):
        out.append(f"<p>{p}</p>")
        if i + 1 in img_positions:
            img = img_positions[i + 1]
            out.append(f'<figure class="post-inline-img"><img src="{img}" alt="{escape(title)}" loading="lazy"></figure>')
    return "\n".join(out)

n_rewritten = 0
n_original = 0
for a in arts:
    body_src = a.get("body_rewritten") or a.get("body_html") or ""
    if a.get("body_rewritten"):
        n_rewritten += 1
    else:
        n_original += 1
    paras = paragraphs_from_text(body_src)
    if not paras:
        paras = [f"This is a feature about {a['title']}. Explore the gallery below for the full visual story."]
    # Image URLs
    img_urls = a.get("body_imgs", []) or []
    final = splice_images(paras, img_urls, a["title"])
    a["final_body_html"] = final
    a["word_count"] = sum(len(re.sub(r"<[^>]+>", "", p).split()) for p in paras)

DATA.write_text(json.dumps(arts, indent=2, ensure_ascii=False))
print(f"Articles with rewrites: {n_rewritten}")
print(f"Articles with original body: {n_original}")
import statistics
wcs = [a["word_count"] for a in arts]
print(f"Word counts: min={min(wcs)}, median={statistics.median(wcs):.0f}, max={max(wcs)}, mean={statistics.mean(wcs):.0f}")
print(f"Articles with 3000+ words: {sum(1 for w in wcs if w >= 3000)}")
print(f"Articles with 1000+ words: {sum(1 for w in wcs if w >= 1000)}")
