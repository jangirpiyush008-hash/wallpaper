"""Parse the 'Rare Historical Photos' docx and update the article in articles_full.json.
Extracts ~60 sections (title, body paragraphs, embedded image) and rebuilds the article body.
"""
import json, re, shutil, zipfile, hashlib
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "articles_full.json"
IMG_DIR = ROOT / "images"
DOCX = Path("/Users/piyushjangir/Downloads/Each of These Rare Historical Photos Has a Unique Story to Tell.docx")
SLUG = "each-of-these-rare-historical-c6"

# --- Step 1: extract embedded image files from the docx ---
with zipfile.ZipFile(DOCX) as z:
    img_data = {}
    for name in z.namelist():
        if name.startswith("word/media/"):
            img_data[Path(name).name] = z.read(name)

print(f"Embedded images: {len(img_data)}")

# Save with stable hashed names + retain .jpg/.png
extracted = {}  # original_name -> images/<hash>_name
for orig_name, data in img_data.items():
    h = hashlib.md5((SLUG + orig_name).encode()).hexdigest()[:8]
    fname = f"{h}_rh_{orig_name}"
    (IMG_DIR / fname).write_bytes(data)
    extracted[orig_name] = f"images/{fname}"
print(f"Saved {len(extracted)} images.")

# --- Step 2: walk docx body in order, mapping inline images to paragraphs ---
doc = Document(str(DOCX))

# Build rel-id -> image filename map
rels = doc.part.rels
rid_to_imgname = {}
for r in rels.values():
    if "image" in r.reltype:
        rid_to_imgname[r.rId] = Path(r.target_ref).name

def paragraph_images(p):
    """Return list of image filenames referenced inside paragraph p (in order)."""
    found = []
    for blip in p._p.iter(qn("a:blip")):
        rid = blip.get(qn("r:embed"))
        if rid and rid in rid_to_imgname:
            found.append(rid_to_imgname[rid])
    return found

# --- Step 3: walk paragraphs in EXACT docx order and emit blocks ---
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

parts = []
first_image_local = None
last_h2_alt = "Photo"

for p in doc.paragraphs:
    text = p.text.strip()
    style = p.style.name
    imgs = paragraph_images(p)

    if style == "Heading 1":
        continue  # site already prints the article title from the header

    if style == "Heading 2":
        if text:
            parts.append(f'<h2 class="gallery-h2">{esc(text)}</h2>')
            last_h2_alt = text
        # If the heading paragraph also carries inline images, emit them too
        for img_name in imgs:
            local = extracted.get(img_name)
            if local:
                parts.append(f'<figure class="post-inline-img"><img src="{local}" alt="{esc(last_h2_alt)}" loading="lazy"></figure>')
                if first_image_local is None:
                    first_image_local = local
        continue

    # Normal body paragraph: emit image(s) inline, then text (preserves docx flow)
    for img_name in imgs:
        local = extracted.get(img_name)
        if local:
            parts.append(f'<figure class="post-inline-img"><img src="{local}" alt="{esc(last_h2_alt)}" loading="lazy"></figure>')
            if first_image_local is None:
                first_image_local = local

    if text:
        if 0 < len(text) < 60 and re.search(r"(Shutterstock|Getty|Alamy|AP Photo|Reuters)", text, re.I):
            parts.append(f'<p class="img-credit"><em>{esc(text)}</em></p>')
        else:
            parts.append(f"<p>{esc(text)}</p>")

body_html = "\n".join(parts)
word_count = sum(len(re.sub(r"<[^>]+>", " ", p).split()) for p in parts)
print(f"Body: {len(parts)} blocks, {word_count} words")

# --- Step 5: update articles_full.json ---
arts = json.loads(DATA.read_text())
target = next((a for a in arts if a["slug"] == SLUG), None)
if not target:
    print("Article not found — was supposed to be added earlier. Aborting.")
    raise SystemExit(1)

# Pick the first encountered image (from docx walk above) as the new hero
if first_image_local:
    target["hero_local"] = first_image_local
    target["thumb_local"] = first_image_local

target["body_rewritten"] = body_html
target["final_body_html"] = body_html
target["word_count"] = word_count

DATA.write_text(json.dumps(arts, indent=2, ensure_ascii=False))
print(f"Updated article '{SLUG}'. Now has {word_count} words.")
