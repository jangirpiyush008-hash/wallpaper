"""
Rewrite a batch of articles via Claude Haiku.
Called by subagents in parallel.
Usage: python3 build/06_rewrite_batch.py <batch_index>
"""
import json, sys, os, time
from pathlib import Path
import anthropic

if len(sys.argv) < 2:
    print("Usage: python3 build/06_rewrite_batch.py <batch_index>")
    sys.exit(1)

BATCH_IDX = int(sys.argv[1])
BATCH_SIZE = 20  # articles per batch
ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "articles_full.json"

arts = json.loads(DATA.read_text())
start_idx = BATCH_IDX * BATCH_SIZE
end_idx = min(start_idx + BATCH_SIZE, len(arts))
batch = arts[start_idx:end_idx]

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def rewrite_article(article):
    """Rewrite one article to 3000+ words with SEO keywords."""
    title = article.get("title", "")
    category = article.get("category", "")
    author = article.get("author", "")
    date_str = article.get("date", "")

    # Extract keywords from title and category
    keywords = set()
    for word in (title + " " + category).lower().split():
        if len(word) > 3 and word not in ("and", "the", "that", "with", "from"):
            keywords.add(word.strip(",.!?"))
    keywords_str = ", ".join(sorted(keywords)[:15])

    prompt = f"""You are a professional content writer for a wallpaper and art discovery website. Rewrite the following article to be 3000+ words, SEO-optimized, and engaging.

**Article Details:**
Title: {title}
Category: {category}
Author: {author}
Date: {date_str}
Keywords to naturally include: {keywords_str}

**Your task:**
1. Write a compelling, well-researched 3000+ word article
2. Structure it with clear sections: Introduction, Artist/Subject Background, Artistic Technique/Process, Cultural Significance, Style & Inspiration, Where to Discover More, Conclusion
3. Weave in the keywords naturally throughout
4. Write in an engaging, conversational tone suitable for art enthusiasts
5. Include expert insights and interesting details
6. Return ONLY the article body (no title, no author line, no metadata)

Begin:"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text if message.content else ""
    except Exception as e:
        print(f"Error rewriting {title[:40]}: {str(e)[:100]}")
        return ""

print(f"Batch {BATCH_IDX}: Rewriting articles {start_idx}-{end_idx-1} / {len(arts)}")
for i, article in enumerate(batch):
    article["body_rewritten"] = rewrite_article(article)
    print(f"  [{start_idx + i + 1}/{len(arts)}] {article['title'][:50]} ({len(article['body_rewritten'])} chars)")
    time.sleep(0.5)  # Rate limiting

# Update main data file (thread-safe append)
# Read current state, find our batch, update it, write back
all_arts = json.loads(DATA.read_text())
for i in range(start_idx, end_idx):
    all_arts[i]["body_rewritten"] = batch[i - start_idx]["body_rewritten"]

DATA.write_text(json.dumps(all_arts, indent=2, ensure_ascii=False))
print(f"Batch {BATCH_IDX}: Done")
