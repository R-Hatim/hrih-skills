#!/usr/bin/env python3
"""Fetch the readable text of a web page verbatim, for voice samples and research.

Summarizing fetch tools paraphrase pages, which destroys exactly what a voice sample is
for (the author's own sentences, rhythm and punctuation). This script keeps the text as
written: it prefers <article> or <main>, drops scripts, navigation, headers, footers and
forms, and keeps headings and paragraphs on their own lines.

Usage:
    python fetch_text.py https://example.com/blog/post -o voice-sample.txt
    python fetch_text.py https://example.com/blog/post            # print to stdout
    python fetch_text.py saved-page.html -o sample.txt            # a local HTML file works too

It does not log in, run JavaScript or get around paywalls or bot protection. If a page
comes back empty or blocked, ask the user to paste the text instead.
Standard library only; works under `python -I`.
"""
import argparse
import re
import sys
import urllib.request
from html.parser import HTMLParser

SKIP = {"script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "button",
        "iframe", "template", "select", "canvas", "figure"}
BLOCK = {"p", "div", "section", "article", "main", "li", "ul", "ol", "br", "h1", "h2", "h3", "h4", "h5", "h6",
         "blockquote", "pre", "tr", "table", "dd", "dt", "hr"}
VOID = {"br", "hr", "img", "input", "meta", "link", "source", "wbr", "area", "base", "col", "embed", "param", "track"}
MAX_BYTES = 5_000_000


class Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # open tags (non-void)
        self.skip_depth = 0
        self.regions = {"article": [], "main": [], "body": []}
        self.active = []         # regions currently open
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            if tag in ("br", "hr"):
                self._emit("\n")
            return
        self.stack.append(tag)
        if tag == "title":
            self._in_title = True
        attrs = dict(attrs)
        hidden = "hidden" in attrs or attrs.get("aria-hidden") == "true" or re.search(
            r"cookie|consent|newsletter-signup|share|social|breadcrumb|related|comments?\b", attrs.get("class", "") + " " + attrs.get("id", ""), re.I)
        if tag in SKIP or (hidden and tag in ("div", "section", "aside", "ul")):
            self.skip_depth += 1
            self.stack[-1] = tag + "#skip"
        if tag in self.regions:
            self.active.append(tag)
        if tag in BLOCK:
            self._emit("\n")
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                self._emit("\n")

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        # pop to the matching tag (HTML in the wild is often unbalanced)
        for i in range(len(self.stack) - 1, -1, -1):
            name = self.stack[i]
            if name.split("#")[0] == tag:
                for closed in self.stack[i:]:
                    if closed.endswith("#skip"):
                        self.skip_depth -= 1
                    base = closed.split("#")[0]
                    if base in self.active:
                        self.active.remove(base)
                del self.stack[i:]
                break
        if tag == "title":
            self._in_title = False
        if tag in BLOCK:
            self._emit("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if self.skip_depth:
            return
        if "pre" not in self.stack:
            data = re.sub(r"\s+", " ", data)  # HTML collapses source whitespace
        self._emit(data)

    def _emit(self, text):
        for region in set(self.active):
            self.regions[region].append(text)


def tidy(raw):
    text = raw.replace("\r", "")
    lines = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in text.split("\n")]
    out, blank = [], False
    for ln in lines:
        if not ln:
            if not blank and out:
                out.append("")
            blank = True
            continue
        out.append(ln)
        blank = False
    return "\n".join(out).strip() + "\n"


def fetch(source):
    if re.match(r"^https?://", source, re.I):
        req = urllib.request.Request(source, headers={
            "User-Agent": "Mozilla/5.0 (compatible; copywriter-skill fetch_text.py; +reads one page for a voice sample)",
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            ctype = resp.headers.get("Content-Type", "")
            data = resp.read(MAX_BYTES)
            charset = resp.headers.get_content_charset() or "utf-8"
        if "html" not in ctype and "xml" not in ctype and not data.lstrip()[:1] == b"<":
            return data.decode(charset, errors="replace"), ""
        html = data.decode(charset, errors="replace")
    else:
        with open(source, encoding="utf-8", errors="replace") as fh:
            html = fh.read()
    parser = Extractor()
    parser.feed(html)
    parser.close()
    for region in ("article", "main", "body"):
        text = tidy("".join(parser.regions[region]))
        if len(text.split()) >= 80:
            return text, parser.title.strip()
    # fall back to the largest region even if short
    best = max(("".join(v) for v in parser.regions.values()), key=len, default="")
    return tidy(best), parser.title.strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch the readable text of a web page verbatim.")
    ap.add_argument("source", help="URL (http/https) or a local .html file")
    ap.add_argument("-o", "--out", help="write the text to this file instead of stdout")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    try:
        text, title = fetch(args.source)
    except Exception as exc:  # network errors, HTTP 4xx/5xx, bad files
        print(f"Could not fetch {args.source}: {exc}. Ask the user to paste the text instead.", file=sys.stderr)
        return 1
    n_words = len(text.split())
    if n_words < 40:
        print(f"Only {n_words} words extracted from {args.source}; the page may need JavaScript or block bots. "
              "Ask the user to paste the text instead.", file=sys.stderr)
    header = f"Source: {args.source}\nTitle: {title}\n\n" if title else f"Source: {args.source}\n\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"Wrote {n_words} words to {args.out}" + (f" (title: {title})" if title else ""))
    else:
        print(header + text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
