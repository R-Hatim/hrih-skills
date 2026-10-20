#!/usr/bin/env python3
"""Lint copy for common AI-writing tells and flat rhythm, or profile a voice sample.

This is an editor's aid, not an AI detector. It points at lines worth a second
look and measures rhythm and punctuation habits. It gives no score and no
verdict: a flagged line can be right in context, and a clean report doesn't
make copy good.

Usage:
    python check_copy.py draft.txt                    # lint a draft
    python check_copy.py draft.txt --voice sample.txt # lint + compare with a voice sample
    python check_copy.py --profile sample.txt         # measure a voice sample
    python check_copy.py draft.md --lang de           # non-English: language-neutral checks only
    python check_copy.py - < draft.txt                # read from stdin
Options: --json for machine-readable output, -o FILE to write the report to a file.

Standard library only. Works on Windows, macOS and Linux, and under `python -I`.
"""
import argparse
import bisect
import json
import re
import statistics
import sys
from collections import Counter

# ---------------------------------------------------------------- patterns

FLAGS = re.IGNORECASE

# Each entry: (kind, severity, regex, hint). Severities follow references/ai-tells.md:
# rewrite = fix every instance; cap = fine occasionally; watch = only in clusters; strip = never ship.
EN_PATTERNS = [
    ("contrast framing", "rewrite",
     r"\bnot\s+(?:just|only|merely|simply)\b[^.!?\n]{1,80}?\b(?:but|it'?s|it’s|it is|they'?re|they’re|we'?re|we’re)\b",
     "state the positive claim directly and back it with a fact"),
    ("contrast framing", "rewrite",
     r"\b(?:it|this|that)(?:'s|’s| is| was)\s+not\s+(?:about\s+|just\s+|only\s+)?[^.!?\n]{1,60}?[,;:—–.]\s*(?:it|this|that)(?:'s|’s| is| was)\b",
     "state the positive claim directly and back it with a fact"),
    ("contrast framing", "rewrite",
     r"\b(?:isn'?t|isn’t|aren'?t|aren’t|wasn'?t|wasn’t|weren'?t|weren’t)\s+(?:just\s+|only\s+|about\s+)?[^.!?\n]{1,60}?[.;,—–]\s*(?:it|they|this|that|we)(?:'s|’s|'re|’re| is| are| was| were)\b",
     "state the positive claim directly and back it with a fact"),
    ("contrast framing", "rewrite",
     r"\bless\s+[\w-]+(?:\s+[\w-]+)?[,.]\s+more\s+[\w-]+",
     "say what it does instead of trading slogans"),
    ("negation list", "rewrite",
     r"(?:^|(?<=[.!?]\s))No\s+[^.!?\n,]{1,30}[.,]\s+No\s+[^.!?\n]{1,30}",
     "say what does happen; keep at most one plain absence next to a CTA"),
    ("'-ing' tail", "rewrite",
     r",\s+(?:ensuring|highlighting|underscoring|showcasing|reflecting|fostering|enhancing|empowering|"
     r"paving the way|contributing to|solidifying|cementing|marking|signall?ing|demonstrating|"
     r"emphasi[sz]ing|reinforcing|elevating|unlocking|making it (?:easier|simpler|possible|effortless))\b",
     "cut the tail; if it held a real consequence, give it its own sentence with a concrete subject"),
    ("copula avoidance", "rewrite",
     r"\b(?:serves|served|serving) as\b|\bstands as\b|\bboasts?\b|\bboasting\b|\bacts as (?:a|an|the)\b",
     "use 'is' or 'has'"),
    ("'whether you're'", "rewrite",
     r"\bwhether you(?:'re|’re| are)\b",
     "write to one reader, or give each real segment its own sentence"),
    ("false range", "rewrite",
     r"(?:^|(?<=[.!?]\s))From\s+[^,.!?\n]{1,40}\s+to\s+[^,.!?\n]{1,40},",
     "name the actual customers or uses"),
    ("stock phrase", "rewrite",
     r"\bin today'?s\b|\bin today’s\b|\bin an era (?:of|where)\b|\bever[- ]evolving\b|\bfast[- ]paced (?:world|landscape|environment)\b|"
     r"\bwhen it comes to\b|\bit'?s no secret\b|\blet'?s (?:dive|delve|break (?:it|this) down|explore)\b|\bdive (?:in|into|deep)\b|"
     r"\bhere'?s the (?:thing|kicker|catch)\b|\bhere'?s what you need to know\b|\blook no further\b|\bimagine a world\b|"
     r"\bsay goodbye to\b|\bin conclusion\b|\bin summary\b|\bat the end of the day\b|\bthe bottom line\b|"
     r"\b(?:and )?that changes everything\b|\bto the next level\b|\bwhat are you waiting for\b|"
     r"\bunlock (?:the )?(?:full |true )?(?:power|potential)\b|\bgame[- ]chang(?:er|ing)\b|\b\w+, reimagined\b|"
     r"\ba testament to\b|\bplays? a (?:pivotal|crucial|vital|key) role\b|\brich (?:cultural )?(?:heritage|tapestry)\b|"
     r"\bnestled in\b|\bembark on\b|\bnavigat(?:e|ing) the (?:complex|complexities|ever|world|landscape)\b|"
     r"\bwe(?:'re|’re| are) (?:thrilled|excited|delighted|proud) to (?:announce|share|introduce|unveil)\b|"
     r"\bready to (?:take|transform|elevate|supercharge|unlock|revolutionize)\b|"
     r"\bit(?:'s|’s| is) (?:important|worth|crucial|essential) to (?:note|remember|mention|understand)\b|"
     r"\bit(?:'s|’s| is) worth (?:noting|mentioning)\b|\bkeep in mind that\b|\bmake all the difference\b",
     "delete it and start or end with a fact"),
    ("stiff transition", "watch",
     r"(?:^|(?<=[.!?]\s))(?:Moreover|Furthermore|Additionally),",
     "rare in human copy: delete it and let the content connect"),
    ("generic moral", "rewrite",
     r"\b(?:careful|proper|thorough|good) planning is (?:essential|key|crucial|everything)\b|"
     r"\bneeds? (?:really |very )?careful planning\b|\bcommunication is key\b|"
     r"\b(?:the right|a good) (?:[\w-]+ )?(?:tool|tools|partner|platform|software) (?:can |will )?make[s]? "
     r"(?:a (?:really |very )?(?:huge|big|real|massive) |all the )difference\b",
     "a moral that says nothing: cut it, or ask the user for the specific lesson"),
    ("stock idiom", "watch",
     r"\b(?:slip(?:ping|s|ped)?|fall(?:ing|s)?|fell) through the cracks\b|\bmove the needle\b|\blow-hanging fruit\b|"
     r"\bpeace of mind\b|\bhit the ground running\b|\ba no-brainer\b|\bbest of both worlds\b|\bthink outside the box\b",
     "name what actually happens instead of the idiom"),
    ("stock closer", "rewrite",
     r"(?:^|(?<=[.!?]\s))(?:Ultimately|Overall|All in all|In the end),\s",
     "end on the next action or the strongest fact, not a recap"),
    ("chat leftover", "strip",
     r"\bhere'?s (?:a|the|your|an) (?:revised|rewritten|updated|improved|polished|refined|new) (?:version|draft|copy)\b|"
     r"\bi hope this helps\b|\blet me know if\b|\bfeel free to (?:adjust|tweak|modify|reach out)\b|\bwould you like me to\b|"
     r"\bas an ai\b|\bas of my (?:last|knowledge)\b|\bi(?:'d|’d| would) be happy to\b|\bcertainly!|\bgreat question\b|"
     r"\babsolutely!|^sure!",
     "remove: notes to the user go outside the copy"),
]

# Stock phrases calqued from English AI prose in other languages (editor heuristics; extend as needed).
LANG_PATTERNS = {
    "de": [("stock phrase", "rewrite",
            r"\bes ist wichtig zu beachten\b|\btauchen wir (?:ein|tiefer)\b|\bzusammenfassend l(?:ä|ae)sst sich sagen\b|"
            r"\bin der heutigen (?:schnelllebigen|digitalen) welt\b|\bnahtlos\w*\b|\bauf das n(?:ä|ae)chste level\b|"
            r"\bnicht nur\b[^.!?\n]{1,60}\bsondern auch\b",
            "calque of an English AI phrase: say the fact plainly")],
    "fr": [("stock phrase", "rewrite",
            r"\bil est important de noter\b|\bplong(?:er|eons) dans\b|\bdans un monde en constante (?:é|e)volution\b|"
            r"\ben conclusion\b|\bsans couture\b|\bau niveau sup(?:é|e)rieur\b|\bnon seulement\b[^.!?\n]{1,60}\bmais aussi\b",
            "calque of an English AI phrase: say the fact plainly")],
}

# Language-neutral residue and placeholders.
ANY_PATTERNS = [
    ("tool residue", "strip",
     r"oaicite|contentReference|turn\d+search\d+|\[cite:?\s*\d+\]|utm_source=chatgpt|【\d+†",
     "remove citation or tool residue"),
    ("unfilled template", "strip",
     r"\[(?!NEED:|VOC:)(?:(?-i:[A-Z][\w ]{1,40})|insert[^\]]{0,40}|your [^\]]{1,40}|company name|product name)\](?!\()|"
     r"\bINSERT[_ ]\w+|\bTBD\b|\bXX%|\blorem ipsum\b",
     "fill it from the brief or turn it into a [NEED: ...] item listed for the user"),
    ("merge field without fallback", "watch",
     r"\{\{\s*[\w.]+\s*\}\}|(?<!\{)\{\s*[\w.]+\s*\}(?!\})",
     "fine in email tools; add a fallback (e.g. {first_name|there}) so nobody gets 'Hi ,'"),
    ("odd characters", "strip",
     "[\\u200b\\u200c\\u200d\\u2060\\ufeff\\u00ad]",
     "invisible characters: remove (never use them to game detectors)"),
]

WATCH_WORDS = sorted(set("""
delve delves delving tapestry testament pivotal crucial intricate meticulous meticulously seamless seamlessly
robust elevate elevates elevating unlock unlocks unleash unleashes empower empowers empowering supercharge
revolutionize revolutionizes revolutionise transformative streamline streamlines streamlined cutting-edge
innovative innovation game-changer game-changing world-class best-in-class effortless effortlessly leverage
leverages leveraging harness harnesses landscape realm journey ecosystem vibrant nestled showcase showcases
showcasing underscore underscores underscoring foster fosters fostering holistic synergy synergies dynamic
comprehensive truly genuinely deeply incredibly quietly notably additionally moreover furthermore paradigm
beacon cornerstone multifaceted unparalleled unprecedented next-level curated bespoke utilize utilizes facilitate
facilitates commence endeavor elevated powerful intuitive
""".split()))

TRANSITIONS = re.compile(
    r"(?:^|(?<=[.!?]\s))(?:Additionally|Moreover|Furthermore|Notably|Importantly|In addition|Indeed|Crucially),",
)

STOPWORDS = set("""
a about above after again against all also am an and any are as at be because been before being below between both
but by can could did do does doing down during each few for from further had has have having he her here hers him his
how i if in into is it its itself just me more most my no nor not now of off on once only or other our ours out over own
same she should so some such than that the their theirs them then there these they this those through to too under
until up very was we were what when where which while who whom why will with would you your yours yourself one get
make like into than them they're we're you're it's that's don't can't won't isn't aren't
""".split())

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⬆↔-⇿✅❌]")
WORD = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*")
ABBREV = re.compile(r"\b(?:e\.g|i\.e|etc|vs|Mr|Mrs|Ms|Dr|St|Inc|Ltd|Co|No|approx|incl|min|max|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.", FLAGS)
SENT_SPLIT = re.compile(r"(?<=[.!?…])[\"'”’)\]]*\s+(?=[\"'“‘(\[]?[A-Z0-9À-ÖØ-ÞČŠŽĆĐ])")
CONTRACTION = re.compile(r"\b\w+(?:n['’]t|['’](?:re|ve|ll|m|d))\b|\b(?:it|that|there|what|here|let|he|she|who|where|how)['’]s\b", FLAGS)
# Fixed pairs ("more or less") end like a list of three but aren't one.
BINOMIAL = re.compile(r"\b(?:more or less|sooner or later|more and more|over and over|again and again|back and forth|"
                      r"on and off|now and then|one way or another|here and there|up and running|odds and ends)$", FLAGS)
TRIAD = re.compile(r"\b[\w'’-]+(?:\s+[\w'’-]+){0,3},\s+[\w'’-]+(?:\s+[\w'’-]+){0,3},?\s+(?:and|or)\s+[\w'’-]+", FLAGS)
PERSON = {
    "I": re.compile(r"\b(?:I|me|my|mine|I'm|I’m|I've|I’ve|I'd|I’d|I'll|I’ll)\b"),
    "we": re.compile(r"\b(?:we|us|our|ours|we're|we’re|we've|we’ve|we'll|we’ll|we'd|we’d)\b", FLAGS),
    "you": re.compile(r"\b(?:you|your|yours|yourself|you're|you’re|you've|you’ve|you'll|you’ll|you'd|you’d)\b", FLAGS),
}


# ---------------------------------------------------------------- parsing

def blank_markdown(text):
    """Return (prose_text, fmt_counts, structure). Markdown markers are replaced by spaces of the
    same length so character offsets (and line numbers) still match the original."""
    counts = Counter()
    lines = text.split("\n")
    out = []
    kinds = []  # per line: 'blank', 'heading', 'bullet', 'text', 'code'
    in_code = False
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            out.append(" " * len(line))
            kinds.append("code")
            continue
        if in_code:
            out.append(" " * len(line))
            kinds.append("code")
            continue
        kind = "text"
        m = re.match(r"^(\s{0,3}#{1,6}\s+)", line)
        if m:
            counts["headings"] += 1
            line = " " * len(m.group(1)) + line[len(m.group(1)):]
            kind = "heading"
        m = re.match(r"^(\s*(?:[-*+•▪◦]|\d{1,2}[.)])\s+)", line)
        if m and kind == "text":
            counts["bullets"] += 1
            if re.match(r"^\s*(?:[-*+•▪◦])\s+\*\*[^*\n]{1,40}\*\*", line):
                counts["bold_label_bullets"] += 1
            if EMOJI.match(line[len(m.group(1)):].strip()[:1] or " "):
                counts["emoji_bullets"] += 1
            line = " " * len(m.group(1)) + line[len(m.group(1)):]
            kind = "bullet"
        elif kind == "text" and EMOJI.match(line.strip()[:1] or " "):
            counts["emoji_bullets"] += 1
        if re.match(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", line):
            counts["rules"] += 1
            line = " " * len(line)
        n_bold = len(re.findall(r"\*\*[^*\n]+\*\*|__[^_\n]+__", line))
        counts["bold"] += n_bold
        line = re.sub(r"\*\*|__", lambda mm: "  ", line)
        # links: keep the link text, blank the URL part
        line = re.sub(r"\]\([^)\s]*\)", lambda mm: " " * len(mm.group(0)), line)
        line = line.replace("[", " ") if re.search(r"\[[^\]]+\]\s{2,}", line) else line
        counts["emoji"] += len(EMOJI.findall(line))
        if not line.strip():
            kind = "blank"
        out.append(line)
        kinds.append(kind)
    return "\n".join(out), counts, kinds


def paragraphs(prose, kinds):
    """Yield (start_offset, text, kind) for prose paragraphs and list items."""
    lines = prose.split("\n")
    offset = 0
    buf, buf_start = [], None
    result = []

    def flush():
        nonlocal buf, buf_start
        if buf:
            body = "\n".join(buf)
            stripped = body.strip()
            # A single short line without terminal punctuation, standing alone, reads as a heading.
            # Consecutive lines are one hard-wrapped paragraph.
            if len(buf) == 1 and len(WORD.findall(stripped)) <= 12 and not re.search(r"[.!?:;,…\"”)]$", stripped):
                result.append((buf_start, body, "heading"))
            else:
                result.append((buf_start, body, "para"))
        buf, buf_start = [], None

    for line, kind in zip(lines, kinds):
        if kind in ("blank", "code"):
            flush()
        elif kind == "heading":
            flush()
            result.append((offset, line, "heading"))
        elif kind == "bullet":
            flush()
            result.append((offset, line, "bullet"))
        else:
            if buf_start is None:
                buf_start = offset
            buf.append(line)
        offset += len(line) + 1
    flush()
    return result


def split_sentences(text):
    protected = ABBREV.sub(lambda m: m.group(0).replace(".", "․"), text.replace("\n", " "))
    parts = [p.replace("․", ".").strip() for p in SENT_SPLIT.split(protected)]
    return [p for p in parts if WORD.search(p)]


def words(text):
    return WORD.findall(text)


# ---------------------------------------------------------------- analysis

def per100(n, total):
    return round(100.0 * n / total, 2) if total else 0.0


def cv(values):
    if len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    return round(statistics.pstdev(values) / mean, 2) if mean else 0.0


def analyze(text, lang="en", voice_metrics=None):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    prose, fmt, kinds = blank_markdown(text)
    newline_pos = [i for i, ch in enumerate(text) if ch == "\n"]

    def line_of(offset):
        return bisect.bisect_right(newline_pos, offset - 1) + 1 if newline_pos else 1

    blocks = paragraphs(prose, kinds)
    all_words = words(prose)
    n_words = len(all_words)
    english = lang.lower().startswith("en")

    # rhythm over prose paragraphs only (headings and bullets excluded)
    para_sentences = []
    for start, body, kind in blocks:
        if kind == "para":
            para_sentences.append((start, body, [len(words(s)) for s in split_sentences(body)]))
    sent_lengths = [n for _, _, lens in para_sentences for n in lens]
    para_lengths = [sum(lens) for _, _, lens in para_sentences if lens]

    findings = []

    def add(offset, kind, severity, excerpt, hint):
        excerpt = re.sub(r"\s+", " ", excerpt).strip()
        if len(excerpt) > 80:
            excerpt = excerpt[:77] + "..."
        findings.append({"line": line_of(offset), "kind": kind, "severity": severity,
                         "excerpt": excerpt, "hint": hint})

    patterns = (EN_PATTERNS if english else LANG_PATTERNS.get(lang.lower()[:2], [])) + ANY_PATTERNS
    for kind, severity, rx, hint in patterns:
        for m in re.finditer(rx, prose, FLAGS | re.MULTILINE):
            add(m.start(), kind, severity, m.group(0), hint)

    # self-answered short questions inside a paragraph ("The result? Happier customers.")
    for start, body, lens in para_sentences:
        sents = split_sentences(body)
        for i, s in enumerate(sents[:-1]):
            if s.endswith("?") and len(words(s)) <= 6:
                tail = s[-15:]
                at = body.find(tail)
                if at >= 0 and body[at + len(tail):].lstrip(" *_\t")[:1] in ("\n", ""):
                    continue  # the question sits on its own line (FAQ style), not a self-answer
                pos = prose.find(s[:20], start)
                add(pos if pos >= 0 else start, "self-answered question", "rewrite", s + " " + sents[i + 1],
                    "give the answer as a statement with the fact that makes it interesting")

    # colon reveals at sentence start ("The best part: ...", "Here's why: ...") in English
    if english:
        for m in re.finditer(r"(?:^|(?<=[.!?]\s))(?:The|Here'?s|Here’s|Our|One)\s+(?:[\w'’]+\s+){0,3}[\w'’]+:\s+\S",
                             prose, re.MULTILINE):
            add(m.start(), "colon reveal", "cap", m.group(0), "fine for a label or a list intro; as a reveal, just say it")

    # stacked sentence-initial transitions
    trans = list(TRANSITIONS.finditer(prose)) if english else []
    if len(trans) >= 2:
        for m in trans:
            add(m.start(), "stacked transition", "cap", m.group(0), "delete it; reorder content if the link breaks")

    # triads: flag paragraphs with more than one, and a document where most paragraphs have one
    triad_paras = 0
    for start, body, kind in blocks:
        if kind != "para":
            continue
        hits = [h for h in TRIAD.finditer(body) if not BINOMIAL.search(h.group(0))] if english else []
        if hits:
            triad_paras += 1
        if len(hits) >= 2:
            for h in hits:
                add(start + h.start(), "list of three", "cap", h.group(0),
                    "if decorative, keep one per section; a real list of three distinct things is fine (don't split it into sentences)")
    n_paras = len(para_sentences)
    if n_paras >= 3 and triad_paras / n_paras > 0.5:
        add(0, "list of three", "cap", f"{triad_paras} of {n_paras} paragraphs contain a triad",
            "reflexive triads: vary list lengths by content; real lists can stay")

    # repeated sentence openers ("Then we... Then we...", "Plus... Plus..."): a tic, often from avoiding another one
    openers = Counter()
    for _, body, _ in para_sentences:
        for s in split_sentences(body):
            first = WORD.findall(s)[:1]
            if first:
                openers[first[0].lower()] += 1
    common = {"the", "a", "an", "you", "your", "we", "our", "i", "it", "this", "that", "they", "there", "if", "and", "but", "so"}
    n_sent = sum(openers.values())
    for word, count in openers.items():
        if word not in common and count >= 3 and count / max(n_sent, 1) >= 0.12:
            add(0, "repeated opener", "watch", f"{count} sentences start with '{word}'",
                "vary how sentences start by restructuring, not by swapping in synonyms")

    # staccato: three or more consecutive very short sentences
    for start, body, lens in para_sentences:
        sents = split_sentences(body)
        run = 0
        for i, n in enumerate(lens):
            run = run + 1 if n <= 3 else 0
            if run == 3:
                frag = " ".join(sents[i - 2:i + 1])
                pos = prose.find(sents[i - 2][:15], start)
                add(pos if pos >= 0 else start, "staccato fragments", "cap", frag,
                    "merge fragments into one sentence with content")
                break

    # flat rhythm per paragraph, and for the whole piece
    for start, body, lens in para_sentences:
        if len(lens) >= 4 and cv(lens) < 0.22 and statistics.mean(lens) >= 8:
            add(start, "flat rhythm", "rewrite", f"{len(lens)} sentences of {min(lens)}-{max(lens)} words",
                "restructure by meaning: give the key fact a short sentence, let the mechanism run long")
    if len(sent_lengths) >= 8 and cv(sent_lengths) < 0.35:
        add(0, "flat rhythm (whole piece)", "watch", f"sentence-length spread (CV) {cv(sent_lengths)}",
            "most human copy varies more; check the longest paragraphs first")
    if len(para_lengths) >= 4 and cv(para_lengths) < 0.2:
        add(0, "blocky paragraphs", "watch", f"{len(para_lengths)} paragraphs of {min(para_lengths)}-{max(para_lengths)} words",
            "size paragraphs by importance, not to match")

    # em dashes: density, with the voice sample's rate as an allowance
    dash_rx = r"—|\s--\s" + (r"|\s–\s" if english else "")
    dashes = [m.start() for m in re.finditer(dash_rx, prose)]
    dash_rate = per100(len(dashes), n_words)
    allowance = 0.33
    if voice_metrics:
        allowance = max(allowance, voice_metrics["per_100_words"]["em_dashes"] * 1.5)
    if dashes and (n_words < 120 or dash_rate > allowance):
        for pos in dashes:
            add(pos, "em dash", "cap", prose[max(0, pos - 30):pos + 30],
                f"rate {dash_rate}/100 words (aim at most {round(allowance, 2)}): use a comma, colon, period or parentheses")

    # exclamation marks beyond the first
    excl = [m.start() for m in re.finditer(r"!", prose)]
    for pos in excl[1:]:
        add(pos, "exclamation mark", "watch", prose[max(0, pos - 40):pos + 1], "let the fact carry the energy")

    # watch words: clusters within a paragraph
    found = Counter()
    for start, body, kind in blocks:
        hits = [w for w in words(body) if w.lower() in WATCH_WORDS] if english else []
        found.update(w.lower() for w in hits)
        if len(set(w.lower() for w in hits)) >= 2:
            add(start, "watch-word cluster", "watch", ", ".join(sorted(set(w.lower() for w in hits))),
                "replace each with the fact it stands for (not a synonym), or cut")

    # formatting
    if fmt["bold_label_bullets"]:
        add(0, "bold-label bullets", "rewrite", f"{fmt['bold_label_bullets']} bullets start with a bold label",
            "write each item as a specific sentence; drop labels that repeat the item")
    if fmt["emoji_bullets"]:
        add(0, "emoji as structure", "strip", f"{fmt['emoji_bullets']} lines start with an emoji",
            "no emoji as bullets or heading markers")
    if english:
        for start, body, kind in blocks:
            if kind == "heading":
                ws = [w for w in words(body) if len(w) > 3]
                if len(ws) >= 3 and all(w[0].isupper() for w in ws):
                    add(start, "title case heading", "watch", body.strip(), "sentence case unless the house style says otherwise")

    findings.sort(key=lambda f: (f["line"], f["kind"]))
    # de-duplicate identical kind+line pairs
    seen, unique = set(), []
    for f in findings:
        key = (f["line"], f["kind"], f["excerpt"][:30])
        if key not in seen:
            seen.add(key)
            unique.append(f)

    content = [w.lower() for w in all_words if len(w) > 3 and w.lower() not in STOPWORDS]
    metrics = {
        "lang": lang,
        "words": n_words,
        "sentences": len(sent_lengths),
        "paragraphs": len(para_lengths),
        "sentence_length": {
            "mean": round(statistics.mean(sent_lengths), 1) if sent_lengths else 0,
            "median": statistics.median(sent_lengths) if sent_lengths else 0,
            "cv": cv(sent_lengths),
            "short_share": round(sum(n <= 8 for n in sent_lengths) / len(sent_lengths), 2) if sent_lengths else 0,
            "long_share": round(sum(n >= 25 for n in sent_lengths) / len(sent_lengths), 2) if sent_lengths else 0,
            "min": min(sent_lengths) if sent_lengths else 0,
            "max": max(sent_lengths) if sent_lengths else 0,
        },
        "paragraph_length": {
            "mean": round(statistics.mean(para_lengths), 1) if para_lengths else 0,
            "cv": cv(para_lengths),
        },
        "per_100_words": {
            "em_dashes": dash_rate,
            "semicolons": per100(prose.count(";"), n_words),
            "colons": per100(len(re.findall(r":(?!//)", prose)), n_words),
            "parentheses": per100(prose.count("("), n_words),
            "questions": per100(prose.count("?"), n_words),
            "exclamations": per100(prose.count("!"), n_words),
            "contractions": per100(len(CONTRACTION.findall(prose)), n_words) if english else None,
            "triads": per100(len(TRIAD.findall(prose)), n_words) if english else None,
            "watch_words": per100(sum(found.values()), n_words) if english else None,
        },
        "person_per_100_words": {k: per100(len(rx.findall(prose)), n_words) for k, rx in PERSON.items()} if english else None,
        "formatting": {k: fmt[k] for k in ("headings", "bullets", "bold", "bold_label_bullets", "emoji", "emoji_bullets", "rules")},
        "open_gaps": len(re.findall(r"\[(?:NEED|VOC):", text)),
        "watch_words_found": dict(found.most_common()),
        "top_words": [w for w, _ in Counter(content).most_common(15)],
    }
    return {"metrics": metrics, "findings": unique}


# ---------------------------------------------------------------- output

SEV_ORDER = {"strip": 0, "rewrite": 1, "cap": 2, "watch": 3}


def fmt_metrics(m):
    s, p = m["sentence_length"], m["per_100_words"]
    lines = [
        f"Words {m['words']} · sentences {m['sentences']} · paragraphs {m['paragraphs']}",
        f"Sentence length: mean {s['mean']}, median {s['median']}, range {s['min']}-{s['max']}, "
        f"spread (CV) {s['cv']}, short (<=8) {int(s['short_share'] * 100)}%, long (>=25) {int(s['long_share'] * 100)}%",
        f"Paragraph length: mean {m['paragraph_length']['mean']} words, spread (CV) {m['paragraph_length']['cv']}",
        "Per 100 words: " + " · ".join(f"{k.replace('_', ' ')} {v}" for k, v in p.items() if v is not None),
    ]
    if m["person_per_100_words"]:
        lines.append("Person per 100 words: " + " · ".join(f"{k} {v}" for k, v in m["person_per_100_words"].items()))
    f = m["formatting"]
    lines.append(f"Formatting: {f['headings']} headings · {f['bullets']} bullet lines · {f['bold']} bold · {f['emoji']} emoji")
    if m["open_gaps"]:
        lines.append(f"Open gaps: {m['open_gaps']} [NEED/VOC] placeholders (list them for the user; resolve before publishing)")
    return lines


def report_text(name, result, voice=None, profile=False):
    m = result["metrics"]
    out = [f"check_copy: {name} (lang {m['lang']})"]
    out += ["  " + line for line in fmt_metrics(m)]
    if profile:
        out.append("  Frequent content words: " + ", ".join(m["top_words"]))
        out.append("  Use these numbers in the voice profile (references/brand-voice.md); read the sample for what numbers miss.")
        return "\n".join(out)
    if voice:
        out.append("")
        out.append("  Compared with the voice sample:")
        vm = voice["metrics"]
        rows = [
            ("avg sentence length", m["sentence_length"]["mean"], vm["sentence_length"]["mean"]),
            ("sentence spread (CV)", m["sentence_length"]["cv"], vm["sentence_length"]["cv"]),
            ("avg paragraph length", m["paragraph_length"]["mean"], vm["paragraph_length"]["mean"]),
        ]
        for key in ("em_dashes", "semicolons", "parentheses", "questions", "exclamations", "contractions"):
            if m["per_100_words"].get(key) is not None:
                rows.append((key.replace("_", " ") + " /100w", m["per_100_words"][key], vm["per_100_words"][key]))
        if m["person_per_100_words"]:
            for k in ("I", "we", "you"):
                rows.append((f"'{k}' /100w", m["person_per_100_words"][k], vm["person_per_100_words"][k]))
        for label, a, b in rows:
            note = ""
            if (a or b) and max(a, b) > 0.3 and (min(a, b) == 0 or max(a, b) / max(min(a, b), 1e-9) > 1.6):
                note = "  <- differs"
            out.append(f"    {label:24s} draft {a:>6}   sample {b:>6}{note}")
    fs = sorted(result["findings"], key=lambda f: (SEV_ORDER.get(f["severity"], 9), f["line"]))
    counts = Counter(f["severity"] for f in fs)
    out.append("")
    out.append(f"  Findings: {len(fs)}" + (" (" + ", ".join(f"{k} {counts[k]}" for k in SEV_ORDER if counts[k]) + ")" if fs else ""))
    if fs and m["words"] >= 600:
        kinds = Counter(f["kind"] for f in fs if f["line"] > 0 and not f["excerpt"][:1].isdigit())
        out.append("  Density per 1,000 words (tells cluster; a few in a long piece can be fine): " +
                   ", ".join(f"{k} {round(1000 * n / m['words'], 1)}" for k, n in kinds.most_common()))
    for f in fs:
        out.append(f"    L{f['line']:<4} {f['severity'].upper():8s} {f['kind']}: \"{f['excerpt']}\"")
        out.append(f"          -> {f['hint']}")
    out.append("")
    out.append("  Not a detector: these are pointers for an editor. Judge each in context; fix from facts, not synonyms.")
    return "\n".join(out)


def read_input(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lint copy for AI-writing tells and rhythm, or profile a voice sample. Not a detector.")
    ap.add_argument("files", nargs="+", help="text or Markdown files ('-' for stdin)")
    ap.add_argument("--profile", action="store_true", help="measure a voice sample instead of linting")
    ap.add_argument("--voice", metavar="SAMPLE", help="compare the draft with a voice sample")
    ap.add_argument("--lang", default="en", help="language code (default en); non-English skips English phrase patterns")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    ap.add_argument("-o", "--out", help="write the report to this file")
    args = ap.parse_args(argv)

    for stream in (sys.stdout, sys.stdin):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    voice =analyze(read_input(args.voice), args.lang) if args.voice else None
    reports, payload = [], []
    for path in args.files:
        result = analyze(read_input(path), args.lang, voice["metrics"] if voice else None)
        payload.append({"file": path, **result})
        reports.append(report_text(path, result, voice=voice, profile=args.profile))
    if args.json:
        data = {"files": payload}
        if voice:
            data["voice_sample"] = {"file": args.voice, "metrics": voice["metrics"]}
        text = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        text = "\n\n".join(reports)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"Report written to {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
