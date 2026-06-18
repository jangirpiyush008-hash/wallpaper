"""Second pass: convert PNGs to JPEG data in-place (keep .png filename).
Browsers content-sniff so this still renders. Skips small PNGs (<150KB).
Resize to 1024px max, quality 70.
"""
import subprocess, tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path("/Users/piyushjangir/Documents/Ankush Website/Newspaper")
IMG = ROOT / "images"

MAX_DIM = "1024"
JPEG_Q = "70"
MIN_SIZE = 150 * 1024  # only attack PNGs over 150KB

pngs = [p for p in IMG.iterdir() if p.suffix.lower() == ".png" and p.stat().st_size > MIN_SIZE]
print(f"PNGs to compress: {len(pngs)}")

def convert(p):
    try:
        size_before = p.stat().st_size
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
            tmp = tf.name
        r = subprocess.run(["sips", "-Z", MAX_DIM, "-s", "format", "jpeg",
                            "-s", "formatOptions", JPEG_Q,
                            str(p), "--out", tmp],
                           capture_output=True, timeout=30)
        if r.returncode == 0:
            # Replace original with JPEG bytes
            Path(tmp).replace(p)
            return size_before, p.stat().st_size, "ok"
        else:
            Path(tmp).unlink(missing_ok=True)
            return size_before, size_before, "fail"
    except Exception as e:
        return p.stat().st_size, p.stat().st_size, f"err:{type(e).__name__}"

total_before = 0
total_after = 0
done = 0
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = [ex.submit(convert, p) for p in pngs]
    for f in as_completed(futs):
        b, a, status = f.result()
        total_before += b
        total_after += a
        done += 1
        if done % 100 == 0:
            print(f"  {done}/{len(pngs)}")

saved = total_before - total_after
print(f"\nPNG→JPEG pass: saved {saved/(1024*1024):.0f} MB ({saved*100/total_before:.0f}% of these PNGs)")
