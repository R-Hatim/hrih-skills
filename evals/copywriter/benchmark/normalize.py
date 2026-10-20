#!/usr/bin/env python3
"""Normalize benchmark texts so a detector compares copy with copy, not formatting.

The same rules apply to every condition. Generated replies (A, B) first lose assistant scaffolding:
  - a leading "Here's the copy:" style line
  - trailing notes, assumptions, alternatives or "What changed" sections
  - unit labels such as "Subject:", "H1:", "CTA:"
  - [NEED: ...] / [VOC: ...] placeholders
Then all texts (A, B and the human controls H) are reduced to plain text: Markdown markers
removed, link text kept, whitespace tidied, paragraphs kept on their own lines. Formatting
counts are recorded before stripping, and stylometrics are computed with the skill's
check_copy.py (descriptive, not a detector).

Usage:
    python normalize.py --run RUN_DIR --human HUMAN_DIR --skill ../../../skills/copywriter
Reads RUN_DIR/text/*.txt and HUMAN_DIR/<id>.txt. Writes RUN_DIR/normalized/<id>__<condition>__<n>.txt
(human files as <id>__human__1.txt) and RUN_DIR/stylometrics.json. Standard library only.
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

LABEL = re.compile(
    r"^\s*(?:[#>*_\-\s]*)\**\s*(?:subject(?: line)?|preview(?: text)?|preheader|h1|h2|h3|headline|subhead(?:line)?|"
    r"sub-?headline|eyebrow|cta|primary cta|secondary cta|button|body|hero|title|meta description|"
    r"section \d+(?: heading)?|section heading|tagline|intro)\s*\**\s*[:\-–—]\s*\**\s*",
    re.I)
LABEL_ONLY = re.compile(r"^\s*[#*_\s]*(?:hero|body|email|subject line|preview text|faq|cta|closing cta|section \d+|"
                        r"linkedin post|launch email|post|copy|homepage copy|final cta|features?)\s*[:*_\s]*$", re.I)
PREAMBLE = re.compile(r"^\s*(?:here(?:'s| is| are)|sure|below (?:is|are)|okay|ok,|i've|i have|great)\b.*$", re.I)
NOTES_START = re.compile(r"^\s*(?:[#*_>\s]*)(?:notes?|assumptions?|what changed|alternatives?|alternative (?:headlines|subject lines|ctas?)|"
                         r"headline alternatives|subject line alternatives|a few notes|open questions|\[?need\b|gaps|to verify|"
                         r"before (?:you )?publish|placeholders|rationale|why this works|options)\b.*$", re.I)
PLACEHOLDER = re.compile(r"\s*\[(?:NEED|VOC|NEEDS SOURCE)[^\]]*\]", re.I)


def load_check_copy(skill_dir):
    sys.dont_write_bytecode = True  # keep __pycache__ out of the skill folder
    path = Path(skill_dir) / "scripts" / "check_copy.py"
    spec = importlib.util.spec_from_file_location("check_copy", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def strip_scaffolding(text):
    lines = text.replace("\r\n", "\n").split("\n")
    # leading preamble (first non-empty line)
    for i, ln in enumerate(lines):
        if ln.strip():
            if PREAMBLE.match(ln) and ln.rstrip().endswith((":", ".")) and len(ln.split()) < 25:
                lines = lines[i + 1:]
            break
    # trailing notes: cut at the first notes heading after some copy, or at a rule followed by notes
    kept, words_so_far = [], 0
    for i, ln in enumerate(lines):
        if words_so_far > 30 and NOTES_START.match(ln) and len(ln.split()) < 12:
            break
        if words_so_far > 30 and re.match(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", ln):
            rest = "\n".join(lines[i + 1:i + 4])
            if NOTES_START.search(rest) or not rest.strip():
                break
        kept.append(ln)
        words_so_far += len(ln.split())
    out = []
    for ln in kept:
        if LABEL_ONLY.match(ln):
            continue
        out.append(LABEL.sub("", ln))
    return "\n".join(out)


def to_plain(text):
    text = text.replace("\r\n", "\n")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = PLACEHOLDER.sub("", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)          # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)       # links -> text
    lines = []
    for ln in text.split("\n"):
        ln = re.sub(r"^\s{0,3}#{1,6}\s+", "", ln)                # headings
        ln = re.sub(r"^\s*(?:[-*+•]|\d{1,2}[.)])\s+", "", ln)     # bullets
        ln = re.sub(r"^\s*>\s?", "", ln)                          # quotes
        ln = re.sub(r"(\*\*|__)(.+?)\1", r"\2", ln)               # bold
        ln = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", ln)  # italics
        if re.match(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", ln):
            ln = ""
        lines.append(re.sub(r"[ \t]+", " ", ln).strip())
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Normalize benchmark texts and compute stylometrics.")
    ap.add_argument("--run", required=True)
    ap.add_argument("--human", required=True)
    ap.add_argument("--skill", required=True, help="skill folder, for scripts/check_copy.py")
    args = ap.parse_args(argv)
    cc = load_check_copy(args.skill)
    run = Path(args.run)
    out_dir = run / "normalized"
    out_dir.mkdir(parents=True, exist_ok=True)
    stylo = {}
    sources = [(p, p.stem, True) for p in sorted((run / "text").glob("*.txt"))]
    sources += [(p, f"{p.stem}__human__1", False) for p in sorted(Path(args.human).glob("*.txt"))]
    for path, stem, generated in sources:
        raw = path.read_text(encoding="utf-8", errors="replace")
        before = cc.analyze(raw)["metrics"]["formatting"]
        body = strip_scaffolding(raw) if generated else raw
        plain = to_plain(body)
        (out_dir / f"{stem}.txt").write_text(plain, encoding="utf-8")
        result = cc.analyze(plain)
        counts = {}
        for f in result["findings"]:
            counts[f["severity"]] = counts.get(f["severity"], 0) + 1
        brief_id, cond, n = stem.split("__")
        stylo[stem] = {"brief": brief_id, "condition": cond, "sample": int(n),
                       "formatting_before": before, "metrics": result["metrics"],
                       "findings_by_severity": counts,
                       "findings": [{"kind": f["kind"], "severity": f["severity"]} for f in result["findings"]]}
    (run / "stylometrics.json").write_text(json.dumps(stylo, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Normalized {len(sources)} texts into {out_dir.resolve()}; stylometrics in {(run / 'stylometrics.json').resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
