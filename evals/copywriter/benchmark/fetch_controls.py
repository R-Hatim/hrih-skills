#!/usr/bin/env python3
"""Rebuild the human control texts of the copywriting benchmark from the Wayback Machine.

Usage:
    python -I fetch_controls.py manifest.json <outdir> [id ...]
    (optional ids restrict the run to those items, e.g. to retry a Wayback timeout)

For every item in the manifest this script downloads the archived page in its
original form (the Wayback "id_" URL, no toolbar), extracts the visible text with
the same logic used to build the benchmark, cuts the excerpt between
anchor_start and anchor_end (both inclusive) and writes <outdir>/<id>.txt.
It then compares the sha256 of each written file with the manifest.

Standard library only. The extraction functions are also used by tools/extract.py.
"""
import gzip
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

USER_AGENT = "copywriting-benchmark-controls/1.0 (research; stdlib urllib)"

# Elements whose whole content is dropped.
SKIP_TAGS = {
    "script", "style", "noscript", "template", "svg", "math", "nav", "footer",
    "iframe", "select", "canvas", "object", "title", "button", "textarea",
}
# Elements dropped when one of their id/class tokens looks like a cookie / consent banner
# (token-level, so e.g. a bakery's "product_cat-cookies" or WordPress' "cookies-not-set"
# body class do not match). html/body/main are never dropped.
COOKIE_TOKEN_RE = re.compile(
    r"^(?:cookie[-_]?(?:notice|banner|consent|law|bar|popup|container|message|warning|alert|box|wrapper|info|policy)\S*"
    r"|cookieconsent\S*|cc[-_](?:window|banner)\S*|gdpr\S*|\S*consent\S*)$", re.I)
NEVER_SKIP = {"html", "body", "main"}
HIDDEN_STYLE_RE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr",
}
# Elements that start and end a line of text.
BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "caption", "center", "dd",
    "details", "dialog", "div", "dl", "dt", "fieldset", "figcaption", "figure",
    "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main",
    "ol", "p", "pre", "section", "summary", "table", "tbody", "td", "tfoot",
    "th", "thead", "tr", "ul", "label", "legend", "body", "html",
}
INVISIBLE_CHARS = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"), None)


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_tag = None
        self.skip_depth = 0

    @staticmethod
    def _should_skip(tag, attrs):
        if tag in SKIP_TAGS:
            return True
        if tag in NEVER_SKIP:
            return False
        a = {k.lower(): (v or "") for k, v in attrs}
        if "hidden" in a or a.get("aria-hidden", "").lower() == "true":
            return True
        if HIDDEN_STYLE_RE.search(a.get("style", "")):
            return True
        tokens = (a.get("id", "") + " " + a.get("class", "")).split()
        if any(COOKIE_TOKEN_RE.match(t) for t in tokens):
            return True
        return False

    def handle_starttag(self, tag, attrs):
        if self.skip_tag is not None:
            if tag == self.skip_tag and tag not in VOID_TAGS:
                self.skip_depth += 1
            return
        if tag not in VOID_TAGS and self._should_skip(tag, attrs):
            self.skip_tag = tag
            self.skip_depth = 1
            return
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.skip_tag is not None:
            if tag == self.skip_tag:
                self.skip_depth -= 1
                if self.skip_depth == 0:
                    self.skip_tag = None
            return
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip_tag is None:
            self.parts.append(data)


def decode_html(raw: bytes) -> str:
    """Bytes of an archived page -> str (gzip aware, meta charset aware)."""
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    m = re.search(rb"<meta[^>]+charset\s*=\s*[\"']?\s*([A-Za-z0-9_\-:.]+)", raw[:8192], re.I)
    enc = m.group(1).decode("ascii", "replace").lower() if m else "utf-8"
    if enc in {"iso-8859-1", "latin1", "latin-1", "us-ascii", "ascii", "windows-1252"}:
        enc = "cp1252"  # what browsers actually use for these labels
    try:
        return raw.decode(enc)
    except (LookupError, UnicodeDecodeError):
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("cp1252", errors="replace")


def extract_text(html_text: str) -> str:
    """Visible text, one block (heading, paragraph, list item, cell) per line."""
    p = TextExtractor()
    p.feed(html_text)
    p.close()
    text = "".join(p.parts).translate(INVISIBLE_CHARS)
    lines = (re.sub(r"\s+", " ", line).strip() for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def _anchor_regex(anchor: str) -> str:
    return r"\s+".join(re.escape(w) for w in anchor.split())


def cut_excerpt(text: str, anchor_start: str, anchor_end: str) -> str:
    """Text from the first anchor_start to the first following anchor_end, inclusive."""
    m1 = re.search(_anchor_regex(anchor_start), text)
    if not m1:
        raise ValueError("anchor_start not found: %r" % anchor_start)
    m2 = re.search(_anchor_regex(anchor_end), text[m1.start():])
    if not m2:
        raise ValueError("anchor_end not found after anchor_start: %r" % anchor_end)
    return text[m1.start(): m1.start() + m2.end()]


def write_text(path: Path, text: str) -> str:
    """Write text as UTF-8 with LF line endings and a final newline; return sha256."""
    data = (text + "\n").encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def fetch(url: str, tries: int = 6) -> bytes:
    delay = 10
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=180) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if attempt == tries:
                raise
            print("  retry %d after error: %s" % (attempt, exc), flush=True)
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    manifest = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    outdir = Path(argv[2]).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    ok = 0
    items = manifest["items"]
    if len(argv) > 3:  # optional: only these ids (e.g. to retry items the Wayback Machine timed out on)
        wanted = set(argv[3:])
        items = [it for it in items if it["id"] in wanted]
    for i, item in enumerate(items):
        if i:
            time.sleep(3)  # be gentle with the Wayback Machine
        print("[%s] %s" % (item["id"], item["wayback_url"]), flush=True)
        try:
            html_text = decode_html(fetch(item["wayback_url"]))
            excerpt = cut_excerpt(extract_text(html_text), item["anchor_start"], item["anchor_end"])
        except Exception as exc:  # report and continue with the next item
            print("  FAILED: %s" % exc, flush=True)
            continue
        out = outdir / ("%s.txt" % item["id"])
        digest = write_text(out, excerpt)
        words = len(excerpt.split())
        match = digest == item.get("sha256")
        ok += match
        print("  wrote %s (%d words) sha256 %s %s" % (
            out, words, digest[:16], "MATCH" if match else "MISMATCH (manifest %s)" % item.get("sha256")), flush=True)
    print("\n%d/%d excerpts match the manifest sha256. Files are in: %s" % (ok, len(items), outdir))
    return 0 if ok == len(items) else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    sys.exit(main(sys.argv))
