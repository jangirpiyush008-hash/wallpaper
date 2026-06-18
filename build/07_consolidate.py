"""
Consolidate all subagent-produced JSON files into articles_full.json.
Look in both project root, project/data/, and /tmp/.
Each file is expected to be {index_str: body_text, ...}.
Merge whatever we find; for articles missing a rewrite, keep original scraped body.
"""
import json, re, glob
from pathlib import Path
from html import unescape

ROOT = Path("/Users/piyushjangir/Documents/Ankush Website/Newspaper")
DATA = ROOT / "data" / "articles_full.json"
arts = json.loads(DATA.read_text())

# Find all candidate JSON files
candidates = []
candidates += list(ROOT.glob("articles_*.json"))
candidates += list((ROOT / "data").glob("articles_*.json"))
candidates += list((ROOT / "data").glob("generated_*.json"))
candidates += list(Path("/tmp").glob("articles_*.json"))
candidates += list(Path("/tmp").glob("extended_articles_*.json"))

# Skip files we don't want
candidates = [c for c in candidates if c.name != "articles_full.json" and c.name != "articles.json"]

print(f"Found {len(candidates)} candidate JSON files")

# Collect rewrites by index, prefer LONGER versions when index appears in multiple files
rewrites = {}
for path in sorted(candidates):
    try:
        text = path.read_text()
        # Try parse
        data = json.loads(text)
        if not isinstance(data, dict):
            continue
        added = 0
        for k, v in data.items():
            try:
                idx = int(k)
            except (ValueError, TypeError):
                continue
            if not isinstance(v, str) or len(v) < 500:
                continue
            # Decode HTML entities and strip code-block markdown if present
            body = unescape(v).strip()
            # Strip outer ```html...``` if present
            body = re.sub(r"^```\w*\s*", "", body)
            body = re.sub(r"\s*```$", "", body)
            # Keep if longer than what we already have
            if idx not in rewrites or len(body) > len(rewrites[idx]):
                rewrites[idx] = body
                added += 1
        if added:
            print(f"  {path.name}: kept {added} rewrites (file size {path.stat().st_size//1024}KB)")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"  SKIP {path.name}: {str(e)[:60]}")

print(f"\nTotal unique rewrites collected: {len(rewrites)}")
print(f"Coverage: {len(rewrites)}/{len(arts)} = {len(rewrites)*100/len(arts):.1f}%")

# Word-count stats
word_counts = [len(b.split()) for b in rewrites.values()]
if word_counts:
    import statistics
    print(f"Word counts: min={min(word_counts)}, median={statistics.median(word_counts):.0f}, max={max(word_counts)}, mean={statistics.mean(word_counts):.0f}")

# Apply to articles
applied = 0
for idx, body in rewrites.items():
    if 0 <= idx < len(arts):
        arts[idx]["body_rewritten"] = body
        applied += 1

print(f"Applied to {applied} articles")

DATA.write_text(json.dumps(arts, indent=2, ensure_ascii=False))
print(f"Saved to {DATA}")
