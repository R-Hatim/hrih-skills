"""Render many gallery thumbnails into one labelled contact-sheet PNG for fast triage.

Most galleries expose public image URLs (reallygoodemails S3 screenshots,
supahero hero crops, posts.design images, ogimage.gallery and navbar.gallery
CDN images; see references/galleries.md). Viewing 10-20 candidates side by
side in one image is much cheaper than scrolling a grid or opening each one.

Usage:
    python contact_sheet.py items.txt --out sheet.png [--cols 5] [--thumb 280] [--max-height 600]

items.txt has one item per line: "label | image_url", or just an image URL.
A JSON array of {"label": ..., "image": ...} also works. Use "-" to read stdin.
Local image paths work too, so you can put your own build's screenshot next
to the references for a direct comparison.

--thumb is each tile's width in px. Images always fill the tile width (never
cropped at the sides); --max-height crops tall ones (full-page screenshots,
emails) to their top part. --max-height 0 shows images whole, which suits
images of similar proportions (hero crops, OG images, emails at thumb ~270).
A whole full-page screenshot becomes a very tall tile, so crop those instead,
or capture the parts you care about. The sheet's height is measured
automatically. For a closer look at a few finalists, rerun with fewer --cols
and a larger --thumb. Tiles whose image fails to load show as a grey box.
"""
import argparse
import html
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # works under `python -I`
from screenshot import find_browser, shoot  # noqa: E402


def to_src(image: str) -> str:
    """Remote URLs pass through; local paths (e.g. your own build's screenshot) become file:// URIs."""
    if image.startswith(("http://", "https://", "file://", "data:")):
        return image
    return pathlib.Path(image).resolve().as_uri()


def read_items(src: str) -> list[dict]:
    text = sys.stdin.read() if src == "-" else pathlib.Path(src).read_text(encoding="utf-8")
    text = text.strip()
    if text.startswith("["):
        items = [{"label": str(i.get("label", "")), "image": i["image"]} for i in json.loads(text)]
    else:
        items = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            label, _, url = line.rpartition("|") if "|" in line else ("", "", line)
            items.append({"label": label.strip(), "image": url.strip()})
    for i in items:
        i["image"] = to_src(i["image"])
    return items


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("items")
    ap.add_argument("--out", required=True, help="output PNG path")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--thumb", type=int, default=280)
    ap.add_argument("--max-height", type=int, default=600)
    args = ap.parse_args()

    items = read_items(args.items)
    if not items:
        print("No items found.", file=sys.stderr)
        return 1
    browser = find_browser()
    if not browser:
        print("No Chrome, Chromium or Edge found; view the images individually instead.", file=sys.stderr)
        return 1

    gap, pad = 16, 20
    width = pad * 2 + args.cols * args.thumb + (args.cols - 1) * gap
    # Every image fills the tile width and is cropped only at the bottom (never
    # the sides), so wide screenshots stay whole horizontally.
    cap = f"max-height:{args.max_height}px;" if args.max_height > 0 else ""

    tiles = "".join(
        f'<figure><div class="img"><img loading="eager" src="{html.escape(i["image"], quote=True)}" alt=""></div>'
        f'<figcaption>{n}. {html.escape(i["label"] or pathlib.PurePosixPath(i["image"]).name)[:60]}</figcaption></figure>'
        for n, i in enumerate(items, 1)
    )
    page = f"""<!doctype html><meta charset="utf-8"><style>
body{{margin:0;padding:{pad}px;background:#f4f4f5;font:13px/1.3 system-ui,sans-serif;color:#18181b}}
.grid{{display:grid;grid-template-columns:repeat({args.cols},{args.thumb}px);gap:{gap}px;align-items:start}}
figure{{margin:0}}
.img{{width:{args.thumb}px;{cap}min-height:60px;background:#d4d4d8;overflow:hidden;border-radius:6px;box-shadow:0 0 0 1px #0000001a}}
img{{width:100%;height:auto;display:block}}
figcaption{{padding-top:6px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}}
</style><div class="grid">{tiles}</div><pre id="h" hidden></pre>
<script>addEventListener('load',()=>setTimeout(()=>{{
document.getElementById('h').textContent='SHEETHEIGHT='+document.querySelector('.grid').getBoundingClientRect().bottom}},300))</script>"""

    out = pathlib.Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="contact-sheet-") as tmp:
        sheet = pathlib.Path(tmp) / "sheet.html"
        sheet.write_text(page, encoding="utf-8")
        # First pass: load the images and measure the sheet, so its height is exact.
        res = subprocess.run(
            [browser, "--headless", "--disable-gpu", "--no-first-run", f"--user-data-dir={tmp}",
             f"--window-size={width},1000", "--virtual-time-budget=15000", "--dump-dom", sheet.as_uri()],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        m = re.search(r"SHEETHEIGHT=([\d.]+)", res.stdout)
        height = min(max(int(float(m.group(1))) + pad, 200), 16000) if m else 2000
        if height == 16000:
            print("Sheet is taller than 16000px and was cut off; use --max-height or fewer items.", file=sys.stderr)
        ok = shoot(browser, sheet.as_uri(), out, width, height, tmp, settle_ms=15000)
    if not ok:
        print("Failed to render the contact sheet.", file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
