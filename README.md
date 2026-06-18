# Wallpaper Data

A static replica of a Newspaper 12.6.6 WordPress theme site featuring 1,020 art and wallpaper articles, built from a CSV source. Each article page is fully rendered HTML with a real hero image, body content, in-article images, related-posts sidebar, and prev/next navigation.

## Run locally

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## What's included

- **1,020 article pages** — `article-*.html`
- **Homepage** with infinite scroll (`index.html`)
- **4 category pages** — Animals, Art, Food & Drinks, Illustrations (each with infinite scroll)
- **21 author pages** — `author-*.html`
- **About Us** + **Privacy Policy** — `about.html`, `privacy.html`
- **2,537 images** in `images/` (compressed JPEG/PNG, max 1280px)
- **`data/articles_full.json`** — full source data (titles, authors, dates, categories, rewritten bodies, image URLs)

## Build pipeline (`build/`)

| Step | Script | Purpose |
|---|---|---|
| 1 | `01_parse_csv.py` | Parse the source CSV, dedupe articles |
| 2 | `02_scrape.py` | Scrape body content + images from source URLs |
| 2b | `02b_fix_category.py` | Fix category extraction from breadcrumbs |
| 3 | `03_images.py` | Download all images locally |
| 5 | `05_rescrape_images.py` | Re-scrape for additional in-body images |
| 7 | `07_consolidate.py` | Merge LLM-rewritten article bodies |
| 8 | `08_build_bodies.py` | Strip Instagram, splice images between paragraphs |
| 9 | `09_generate_v2.py` | Render all HTML pages |
| 10 | `10_compress_images.py` | Compress images (sips, 1280px max, JPEG q75) |
| 11 | `11_compress_png.py` | Convert large PNGs to JPEG bytes in-place |

## Layout

- `assets/style.css` — single stylesheet, Newspaper-12.6.6 inspired
- `assets/infinite.js` — client-side infinite-scroll loader
- `images/` — all images
- `data/articles.json` — minimal article metadata
- `data/articles_full.json` — full enriched articles with bodies
- `build/` — Python pipeline scripts
