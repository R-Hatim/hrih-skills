"""Screenshot a local HTML file (or URL) with a locally installed headless Chrome/Chromium/Edge.

Use this to look at your own build next to the references when the browser
tools can't open local files (the built-in browser and some Playwright setups
block file://, and sandboxes may forbid starting a local web server).

Usage:
    python screenshot.py <file.html | url> [--out-dir DIR] [--height 2400] [--full]
                         [--widths 1440,390] [--no-mobile] [--dark]

Writes <name>-desktop.png (1440 wide) and <name>-mobile.png (a 390px phone
viewport framed on a 500px canvas) and prints their paths; open them with your
image-reading tool. Also handy for a true 1440px view of a LIVE reference site
when your browser pane is narrow: `screenshot.py https://site.com --height 900 --no-mobile`.

--height   capture height in CSS px (default 2400). Use ~900 to judge only the
           first screen.
--widths   viewport widths to capture (default 1440,390). Other widths are
           named <name>-<w>px.png. Check in-between breakpoints with e.g.
           1440,1024,820,390, or capture an email at its own width with 700,390.
--full     capture the WHOLE page as numbered parts of --height px each
           (<name>-desktop-1of4.png ...), like scrolling one screen at a
           time, so every section stays legible instead of shrinking into one
           giant image. --height is then also the viewport height (100vh).
           Try --full --height 1200. Local files only.
--dark     render with prefers-color-scheme: dark (files get a -dark suffix)
           to check dark-mode CSS, which matters especially for email.

Sites that forbid framing may render blank on mobile or with --full; that only
affects URLs, not your own local files.
"""
import argparse
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

CANDIDATES = [
    # Windows
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    # macOS
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
PATH_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge", "microsoft-edge"]


def find_browser() -> str | None:
    for c in CANDIDATES:
        if os.path.isfile(c):
            return c
    for n in PATH_NAMES:
        p = shutil.which(n)
        if p:
            return p
    return None


def shoot(browser: str, target: str, out: pathlib.Path, width: int, height: int, profile: str,
          dark: bool = False, settle_ms: int = 4000, extra: list[str] | None = None) -> bool:
    cmd = [
        browser, "--headless", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
        f"--user-data-dir={profile}", f"--window-size={width},{height}",
        f"--virtual-time-budget={settle_ms}",  # let web fonts, images and simple JS settle
        *(extra or []),
        f"--screenshot={out}", target,
    ]
    if dark:
        cmd.insert(1, "--force-dark-mode")  # sets prefers-color-scheme: dark
    if out.exists():
        out.unlink()
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    return out.exists() and out.stat().st_size > 0


def frame(url: str, frame_w: int, frame_h: int, scroll_y: int, folder: str, name: str, measure: bool = False) -> str:
    """A page showing `url` in a frame_w x frame_h iframe, scrolled to scroll_y.

    Scrolling a viewport-sized iframe is how we capture successive slices of a
    long page without an image library, and it behaves like real scrolling
    (sticky headers, 100vh sections and scroll-reveal animations stay normal).
    With measure=True the wrapper writes the framed page's full height into the
    DOM for --dump-dom to read. Both need --allow-file-access-from-files, so
    they work for local files, not for remote URLs.
    """
    body = ""
    if measure:
        body = ("let h=0;try{const d=f.contentDocument;"
                "h=Math.max(d.documentElement.scrollHeight,d.body?d.body.scrollHeight:0)}catch(e){}"
                "document.getElementById('h').textContent='PAGEHEIGHT='+h;")
    elif scroll_y:
        # Force instant scrolling: pages with `scroll-behavior: smooth` would
        # otherwise still be mid-animation when the screenshot is taken.
        body = ("try{const w=f.contentWindow,r=w.document.documentElement;"
                "r.style.setProperty('scroll-behavior','auto','important');"
                f"w.scrollTo({{top:{scroll_y},left:0,behavior:'instant'}})}}catch(e){{}}")
    script = (f"<script>const f=document.querySelector('iframe');"
              f"f.addEventListener('load',()=>setTimeout(()=>{{{body}}},600))</script>") if body else ""
    wrapper = pathlib.Path(folder) / f"{name}.html"
    wrapper.write_text(
        '<!doctype html><body style="margin:0;overflow:hidden;background:#d4d4d8">'
        f'<iframe src="{url}" style="display:block;margin:0 auto;width:{frame_w}px;'
        f'height:{frame_h}px;border:0;background:#fff"></iframe><pre id="h" hidden></pre>{script}</body>',
        encoding="utf-8",
    )
    return wrapper.as_uri()


def measure_height(browser: str, url: str, frame_w: int, window_w: int, frame_h: int, profile: str, dark: bool) -> int:
    probe = frame(url, frame_w, frame_h, 0, profile, f"measure-{frame_w}", measure=True)
    cmd = [browser, "--headless", "--disable-gpu", "--no-first-run", "--allow-file-access-from-files",
           f"--user-data-dir={profile}", f"--window-size={window_w},{frame_h}",
           "--virtual-time-budget=6000", "--dump-dom", probe]
    if dark:
        cmd.insert(1, "--force-dark-mode")
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    m = re.search(r"PAGEHEIGHT=(\d+)", res.stdout)
    return int(m.group(1)) if m else 0


def capture_full(browser: str, url: str, stem: str, out_dir: pathlib.Path, label: str, frame_w: int,
                 window_w: int, part_h: int, profile: str, dark: bool, suffix: str) -> bool:
    total = measure_height(browser, url, frame_w, window_w, part_h, profile, dark)
    if not total:
        print(f"Couldn't measure the {label} page height (--full works for local files, not remote URLs); use --height instead.", file=sys.stderr)
        return False
    total = min(total, 40000)
    parts = max(1, math.ceil(total / part_h))
    ok = True
    for i in range(parts):
        # The last part scrolls only as far as the page allows, so it may overlap the previous one.
        target = frame(url, frame_w, part_h, i * part_h, profile, f"{label}-part{i + 1}")
        out = out_dir / f"{stem}-{label}{suffix}-{i + 1}of{parts}.png"
        cmd_ok = shoot(browser, target, out, window_w, part_h, profile, dark=dark, extra=["--allow-file-access-from-files"])
        print(out if cmd_ok else f"Failed: {label} part {i + 1}", file=sys.stdout if cmd_ok else sys.stderr)
        ok &= cmd_ok
    print(f"{label}: page is {total}px tall, captured in {parts} part(s) of {part_h}px", file=sys.stderr)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="local .html file or http(s) URL")
    ap.add_argument("--out-dir", default=None, help="where to write PNGs (default: next to the file, or cwd for URLs)")
    ap.add_argument("--height", type=int, default=2400, help="capture height; with --full, the height of each part")
    ap.add_argument("--full", action="store_true", help="capture the whole page, split into parts of --height px")
    ap.add_argument("--widths", default="1440,390", help="comma-separated viewport widths (default 1440,390)")
    ap.add_argument("--no-mobile", action="store_true", help="drop widths under 500 (the phone view)")
    ap.add_argument("--dark", action="store_true", help="emulate prefers-color-scheme: dark")
    args = ap.parse_args()
    try:
        widths = [int(w) for w in args.widths.split(",") if w.strip()]
    except ValueError:
        print("--widths must be comma-separated integers, e.g. 1440,1024,390", file=sys.stderr)
        return 2
    if args.no_mobile:
        widths = [w for w in widths if w >= 500]

    browser = find_browser()
    if not browser:
        print("No Chrome, Chromium or Edge found. Render the page another way (artifact preview, Playwright) or skip the visual check and say so.", file=sys.stderr)
        return 1

    if args.target.startswith(("http://", "https://", "file://")):
        host = re.sub(r"^www\.", "", urllib.parse.urlparse(args.target).netloc)
        url, stem, default_dir = args.target, re.sub(r"[^\w.-]", "_", host) or "page", pathlib.Path.cwd()
    else:
        path = pathlib.Path(args.target).resolve()
        if not path.exists():
            print(f"Not found: {path}", file=sys.stderr)
            return 1
        url, stem, default_dir = path.as_uri(), path.stem, path.parent
    out_dir = pathlib.Path(args.out_dir).resolve() if args.out_dir else default_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "-dark" if args.dark else ""

    # (label, page width, window width). Headless Chrome won't make a window
    # narrower than 500px, so a plain 390px capture would crop a 500px layout.
    # Narrow widths therefore frame the page in an iframe of that width (a true
    # phone-width viewport, so media queries fire) centered on a 500px canvas.
    def label_for(w: int) -> str:
        return {1440: "desktop", 390: "mobile"}.get(w, f"{w}px")
    views = [(label_for(w), w, max(w, 500)) for w in widths]
    ok = True
    with tempfile.TemporaryDirectory(prefix="shot-profile-") as profile:
        for label, frame_w, window_w in views:
            if args.full:
                ok &= capture_full(browser, url, stem, out_dir, label, frame_w, window_w,
                                   args.height, profile, args.dark, suffix)
                continue
            target = url if frame_w >= 500 else frame(url, frame_w, args.height, 0, profile, label)
            out = out_dir / f"{stem}-{label}{suffix}.png"
            if shoot(browser, target, out, window_w, args.height, profile, dark=args.dark):
                print(out)
            else:
                ok = False
                print(f"Failed to capture {label} with {browser}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
