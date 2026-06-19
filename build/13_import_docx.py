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

# --- Step 3: parse into sections ---
sections = []
current = None
header_paragraphs = []

for p in doc.paragraphs:
    text = p.text.strip()
    style = p.style.name
    imgs = paragraph_images(p)

    if style == "Heading 1":
        continue  # site already has the title separately
    if style == "Heading 2":
        # start a new section
        if current:
            sections.append(current)
        current = {"title": text, "paras": [], "imgs": []}
        continue
    # body paragraph
    if current is None:
        # pre-first-section content = intro
        if text:
            header_paragraphs.append(text)
        if imgs:
            for n in imgs:
                if n not in [x for s in sections for x in s["imgs"]]:
                    pass  # will be handled below
        continue
    if imgs:
        current["imgs"].extend(imgs)
    if text:
        current["paras"].append(text)

if current:
    sections.append(current)

print(f"Sections parsed: {len(sections)}")

# Filter: keep only sections that have at least 1 image OR a substantial title (drop empty/heading-like noise)
sections = [s for s in sections if (s["imgs"] or len(s["title"]) < 80)]

# --- Step 4: build the HTML body ---
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

parts = []
# Intro
for hp in header_paragraphs[:6]:
    if hp and len(hp) > 20:
        parts.append(f"<p>{esc(hp)}</p>")

# Sections
for s in sections:
    parts.append(f'<h2 class="gallery-h2">{esc(s["title"])}</h2>')
    for img_name in s["imgs"][:1]:  # one image per section is typical
        local = extracted.get(img_name)
        if local:
            parts.append(f'<figure class="post-inline-img"><img src="{local}" alt="{esc(s["title"])}" loading="lazy"></figure>')
    for para in s["paras"]:
        # Skip very short credit lines (image credits like "Historia/Shutterstock")
        if 0 < len(para) < 60 and re.search(r"(Shutterstock|Getty|Alamy|AP Photo|Reuters)", para, re.I):
            parts.append(f'<p class="img-credit"><em>{esc(para)}</em></p>')
        else:
            parts.append(f"<p>{esc(para)}</p>")

body_html = "\n".join(parts)
word_count = sum(len(re.sub(r"<[^>]+>", " ", p).split()) for p in parts)
print(f"Body: {len(parts)} blocks, {word_count} words")

# --- Step 5: update articles_full.json ---
arts = json.loads(DATA.read_text())
target = next((a for a in arts if a["slug"] == SLUG), None)
if not target:
    print("Article not found — was supposed to be added earlier. Aborting.")
    raise SystemExit(1)

# Pick the first image as the new hero (more relevant than the OG image)
first_img = None
for s in sections:
    if s["imgs"]:
        first_img = extracted.get(s["imgs"][0])
        break

if first_img:
    target["hero_local"] = first_img
    target["thumb_local"] = first_img

target["body_rewritten"] = body_html
target["final_body_html"] = body_html
target["word_count"] = word_count

DATA.write_text(json.dumps(arts, indent=2, ensure_ascii=False))
print(f"Updated article '{SLUG}'. Now has {word_count} words.")
