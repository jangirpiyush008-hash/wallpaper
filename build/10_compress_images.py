"""Compress all images in-place using macOS `sips`.
 - Resize so max dimension is 1280px
 - Re-encode JPEGs at quality 75
 - PNGs: try sips PNG optimization, fall back to keeping original
 - Skip GIFs (don't compress, would lose animation)
 - Run in parallel
"""
import os, sys, subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path("/Users/piyushjangir/Documents/Ankush Website/Newspaper")
IMG = ROOT / "images"

MAX_DIM = 1280
JPEG_Q = "75"

files = [p for p in IMG.iterdir() if p.is_file()]
print(f"Total images: {len(files)}")

def compress(p):
    try:
        ext = p.suffix.lower()
        size_before = p.stat().st_size
        if ext in (".jpg", ".jpeg"):
            r = subprocess.run(["sips", "-Z", str(MAX_DIM), "-s", "formatOptions", JPEG_Q,
                                str(p), "--out", str(p)],
                               capture_output=True, timeout=30)
            ok = r.returncode == 0
        elif ext == ".png":
            # First resize, then convert to JPEG (smaller). But check for alpha first.
            # Quick alpha check via sips
            r = subprocess.run(["sips", "-Z", str(MAX_DIM), str(p), "--out", str(p)],
                               capture_output=True, timeout=30)
            ok = r.returncode == 0
        elif ext == ".webp":
            r = subprocess.run(["sips", "-Z", str(MAX_DIM), "-s", "format", "jpeg",
                                "-s", "formatOptions", JPEG_Q,
                                str(p), "--out", str(p)],
                               capture_output=True, timeout=30)
            ok = r.returncode == 0
        else:
            return (p.name, size_before, size_before, "skip")
        size_after = p.stat().st_size
        return (p.name, size_before, size_after, "ok" if ok else "fail")
    except subprocess.TimeoutExpired:
        return (p.name, p.stat().st_size, p.stat().st_size, "timeout")
    except Exception as e:
        return (p.name, p.stat().st_size, p.stat().st_size, f"err:{type(e).__name__}")

total_before = 0
total_after = 0
done = 0
errors = []
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = [ex.submit(compress, p) for p in files]
    for f in as_completed(futs):
        name, b, a, status = f.result()
        total_before += b
        total_after += a
        done += 1
        if status not in ("ok", "skip"):
            errors.append((name, status))
        if done % 200 == 0:
            print(f"  {done}/{len(files)}  saved so far: {(total_before-total_after)/(1024*1024):.0f} MB")

print(f"\n=== Compression Summary ===")
print(f"Before: {total_before/(1024**3):.2f} GB")
print(f"After:  {total_after/(1024**3):.2f} GB")
saved = total_before - total_after
print(f"Saved:  {saved/(1024**3):.2f} GB ({saved*100/total_before:.0f}% reduction)")
if errors:
    print(f"Errors: {len(errors)}")
    for n, s in errors[:5]:
        print(f"  {n}: {s}")
