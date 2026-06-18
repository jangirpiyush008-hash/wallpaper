"""Orchestrator: manage batches of article rewrites via Claude Haiku.
Runs locally, spawns rewrites via API, collects results, merges into articles_full.json."""

import json, os, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import anthropic

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "articles_full.json"
RESULTS_DIR = ROOT / "data" / "rewrite_batches"
RESULTS_DIR.mkdir(exist_ok=True)

arts = json.loads(DATA.read_text())
BATCH_SIZE = 20
NUM_BATCHES = (len(arts) + BATCH_SIZE - 1) // BATCH_SIZE
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def rewrite_article_text(title, category, old_body):
    """Generate 3000+ word rewrite for one article."""
    keywords = set()
    for word in (title + " " + category).lower().split():
        if len(word) > 3 and word not in ("and", "the", "that", "with", "from", "wallpaper"):
            keywords.add(word.strip(",.!?'\""))
    keywords_str = ", ".join(sorted(keywords)[:12])

    prompt = f"""Write a compelling, SEO-optimized 3000+ word article for a wallpaper/art discovery site.

Title: {title}
Category: {category}
Keywords: {keywords_str}

Structure: Introduction → Artist/Subject Background → Artistic Technique → Cultural Significance → Inspiration & Style → Where to Discover → Conclusion

Return ONLY the article body (no title, no metadata). Be engaging, informative, and natural."""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4500,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text if msg.content else ""

def process_batch(batch_idx):
    """Rewrite one batch of articles."""
    start = batch_idx * BATCH_SIZE
    end = min(start + BATCH_SIZE, len(arts))
    batch_arts = arts[start:end]
    results = {}

    for i, article in enumerate(batch_arts):
        try:
            rewritten = rewrite_article_text(article["title"], article["category"], article.get("body_html", ""))
            results[start + i] = rewritten
            print(f"  Batch {batch_idx}: [{i+1}/{len(batch_arts)}] {article['title'][:40]} ({len(rewritten)} chars)")
            time.sleep(0.3)
        except Exception as e:
            print(f"  Batch {batch_idx}: Error on {article['title'][:40]}: {str(e)[:60]}")
            results[start + i] = ""

    # Save batch results to temp file
    batch_file = RESULTS_DIR / f"batch_{batch_idx}.json"
    batch_file.write_text(json.dumps(results, indent=2))
    return batch_idx

print(f"Rewriting {len(arts)} articles in {NUM_BATCHES} batches (size {BATCH_SIZE})...")
print(f"Using claude-haiku-4-5-20251001")

# Process batches with concurrency
MAX_WORKERS = 5  # Keep concurrency low to avoid rate limits
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
    futures = [ex.submit(process_batch, i) for i in range(NUM_BATCHES)]
    for f in as_completed(futures):
        batch_idx = f.result()
        print(f"✓ Batch {batch_idx} complete")

# Merge all batch results back into articles_full.json
print("\nMerging results...")
all_arts = json.loads(DATA.read_text())
for batch_file in sorted(RESULTS_DIR.glob("batch_*.json")):
    results = json.loads(batch_file.read_text())
    for idx_str, body in results.items():
        idx = int(idx_str)
        if idx < len(all_arts):
            all_arts[idx]["body_rewritten"] = body

DATA.write_text(json.dumps(all_arts, indent=2, ensure_ascii=False))

# Stats
rewritten_count = sum(1 for a in all_arts if a.get("body_rewritten"))
avg_len = sum(len(a.get("body_rewritten", "")) for a in all_arts) / len(all_arts) if all_arts else 0
print(f"\nComplete: {rewritten_count}/{len(all_arts)} articles rewritten")
print(f"Average length: {avg_len:.0f} chars (~{avg_len/200:.0f} words)")
