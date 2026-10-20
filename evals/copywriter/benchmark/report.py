#!/usr/bin/env python3
"""Summarize the detector benchmark: Binoculars scores plus stylometrics, by condition.

Conditions: human (H, pre-2020 controls), without_skill (A), with_skill (B).
Binoculars: lower score = more machine-like. Flag thresholds are the published ones (low-FPR
mode 0.8536, accuracy mode 0.9015). Statistics resample briefs, not texts (cluster bootstrap),
because samples of the same brief are not independent.

Usage:
    python report.py --run RUN_DIR [--scores RUN_DIR/binoculars.json]
Writes RUN_DIR/results.csv and RUN_DIR/report.md and prints where they went. Standard library only.
"""
import argparse
import csv
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

CONDS = ["human", "without_skill", "with_skill"]
LABEL = {"human": "H human (pre-2020)", "without_skill": "A Claude, no skill", "with_skill": "B Claude + skill"}


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - r) / d), min(1.0, (c + r) / d))


def auroc(pos, neg):
    """P(score of a human text > score of a generated text); 0.5 = indistinguishable, 1 = perfectly separated."""
    if not pos or not neg:
        return float("nan")
    wins = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return wins / (len(pos) * len(neg))


def bootstrap(briefs, fn, reps=2000, seed=7):
    rng = random.Random(seed)
    vals = []
    for _ in range(reps):
        sample = [rng.choice(briefs) for _ in briefs]
        v = fn(sample)
        if v == v:  # not NaN
            vals.append(v)
    vals.sort()
    if not vals:
        return (float("nan"), float("nan"))
    return (vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1])


def fmt(x, nd=3):
    return "n/a" if x != x else f"{x:.{nd}f}"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Summarize the detector benchmark.")
    ap.add_argument("--run", required=True)
    ap.add_argument("--scores", nargs="*", help="Binoculars JSON file(s), merged (default RUN_DIR/binoculars*.json)")
    args = ap.parse_args(argv)
    run = Path(args.run)
    stylo = json.loads((run / "stylometrics.json").read_text(encoding="utf-8"))
    score_files = [Path(p) for p in args.scores] if args.scores else sorted(run.glob("binoculars*.json"))
    bino = {}
    meta = {}
    for scores_path in score_files:
        data = json.loads(scores_path.read_text(encoding="utf-8"))
        meta = meta or {k: v for k, v in data.items() if k != "results"}
        bino.update({r["file"][:-4]: r for r in data["results"]})

    rows = []
    for stem, s in sorted(stylo.items()):
        m, b = s["metrics"], bino.get(stem, {})
        rows.append({
            "text": stem, "brief": s["brief"], "type": s["brief"].split("-")[0], "condition": s["condition"],
            "words": m["words"],
            "binoculars": b.get("score", ""), "flag_low_fpr": b.get("flag_low_fpr", ""), "flag_accuracy": b.get("flag_accuracy", ""),
            "tokens": b.get("tokens", ""),
            "sent_mean": m["sentence_length"]["mean"], "sent_cv": m["sentence_length"]["cv"],
            "em_dashes_100w": m["per_100_words"]["em_dashes"], "contractions_100w": m["per_100_words"]["contractions"],
            "triads_100w": m["per_100_words"]["triads"], "watch_words_100w": m["per_100_words"]["watch_words"],
            "rewrite_findings": s["findings_by_severity"].get("rewrite", 0) + s["findings_by_severity"].get("strip", 0),
            "bullets_before": s["formatting_before"]["bullets"], "headings_before": s["formatting_before"]["headings"],
        })
    with open(run / "results.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    by = defaultdict(list)
    for r in rows:
        by[r["condition"]].append(r)
    briefs = sorted({r["brief"] for r in rows if r["condition"] != "human"})

    def per_brief_mean(cond, key, subset):
        vals = [statistics.mean([float(r[key]) for r in by[cond] if r["brief"] == b and r[key] != ""])
                for b in subset if any(r["brief"] == b and r[key] != "" for r in by[cond])]
        return statistics.mean(vals) if vals else float("nan")

    out = ["# Detector benchmark report", ""]
    if meta:
        out.append(f"Binoculars ({meta.get('observer')} / {meta.get('performer')}, {meta.get('dtype')}, {meta.get('device')}, "
                   f"max {meta.get('max_tokens')} tokens), run {meta.get('run_at')}. Lower score = more machine-like.")
    out.append(f"Texts: " + ", ".join(f"{LABEL[c]} {len(by[c])}" for c in CONDS) + f"; briefs: {len(briefs)}.")
    out.append("")
    if bino:
        out += ["## Binoculars", "",
                "| Condition | n | Mean score (95% CI, by brief) | Median | Flagged, low-FPR threshold (95% CI) | Flagged, accuracy threshold |",
                "|---|---|---|---|---|---|"]
        for c in CONDS:
            vals = [float(r["binoculars"]) for r in by[c] if r["binoculars"] != ""]
            if not vals:
                continue
            k1 = sum(1 for r in by[c] if r["flag_low_fpr"] is True)
            k2 = sum(1 for r in by[c] if r["flag_accuracy"] is True)
            lo, hi = bootstrap(briefs, lambda bs, c=c: per_brief_mean(c, "binoculars", bs))
            wl, wh = wilson(k1, len(vals))
            out.append(f"| {LABEL[c]} | {len(vals)} | {fmt(statistics.mean(vals))} ({fmt(lo)} to {fmt(hi)}) | {fmt(statistics.median(vals))} | "
                       f"{k1}/{len(vals)} ({wl * 100:.0f}% to {wh * 100:.0f}%) | {k2}/{len(vals)} |")
        hum = [float(r["binoculars"]) for r in by["human"] if r["binoculars"] != ""]
        out += ["", "**Separability from human copy** (AUROC: 0.5 = indistinguishable, 1.0 = perfectly separated; "
                "lower means the condition reads more like the human controls):", ""]
        for c in ("without_skill", "with_skill"):
            gen = [float(r["binoculars"]) for r in by[c] if r["binoculars"] != ""]

            def au(bs, c=c):
                h = [float(r["binoculars"]) for r in by["human"] if r["brief"] in bs and r["binoculars"] != ""]
                g = [float(r["binoculars"]) for r in by[c] if r["brief"] in bs and r["binoculars"] != ""]
                return auroc(h, g)
            lo, hi = bootstrap(briefs, au)
            out.append(f"- H vs {LABEL[c]}: AUROC {fmt(auroc(hum, gen))} (95% CI {fmt(lo)} to {fmt(hi)})")
        diffs = []
        for b in briefs:
            a = [float(r["binoculars"]) for r in by["without_skill"] if r["brief"] == b and r["binoculars"] != ""]
            s_ = [float(r["binoculars"]) for r in by["with_skill"] if r["brief"] == b and r["binoculars"] != ""]
            if a and s_:
                diffs.append(statistics.mean(s_) - statistics.mean(a))
        if diffs:
            rng = random.Random(11)
            boots = sorted(statistics.mean([rng.choice(diffs) for _ in diffs]) for _ in range(2000))
            out += ["", f"**Paired, per brief (B minus A):** mean {fmt(statistics.mean(diffs))} "
                    f"(95% CI {fmt(boots[50])} to {fmt(boots[1949])}); B scored higher (more human-like) on "
                    f"{sum(d > 0 for d in diffs)} of {len(diffs)} briefs."]
        out.append("")

    out += ["## Stylometrics (descriptive, not a detector)", "",
            "Means per text after normalization. Compare A and B with H, not with zero: human marketing copy has triads, dashes and buzzwords too.", "",
            "| Condition | Words | Sentence mean | Sentence spread (CV) | Em dashes /100w | Contractions /100w | Triads /100w | Watch words /100w | Rewrite-level findings |",
            "|---|---|---|---|---|---|---|---|---|"]
    for c in CONDS:
        if not by[c]:
            continue
        def mean(key):
            vals = [float(r[key]) for r in by[c] if r[key] not in ("", None)]
            return statistics.mean(vals) if vals else float("nan")
        out.append(f"| {LABEL[c]} | {mean('words'):.0f} | {mean('sent_mean'):.1f} | {mean('sent_cv'):.2f} | {mean('em_dashes_100w'):.2f} | "
                   f"{mean('contractions_100w'):.2f} | {mean('triads_100w'):.2f} | {mean('watch_words_100w'):.2f} | {mean('rewrite_findings'):.1f} |")
    out += ["", "## Caveats", "",
            "- A detector score is not a quality score, and the skill is not tuned against it. Blind human review is the primary judge.",
            "- Small sample: briefs, not texts, are the unit of analysis. Wide intervals are expected and should be read as such.",
            "- Marketing copy is outside every validated detector domain. Short, formulaic and professionally edited human copy is the known false-positive zone, so the human false-positive rate above is part of the result.",
            "- Zero-shot detectors like Binoculars have been weak on Claude output in published tests; a model newer than any published evaluation is used here.",
            "- Human controls date from 2019 or earlier and differ in era and topic fashions from 2026 copy.",
            "- If Binoculars ran in bfloat16 on CPU, scores can differ slightly from the reference GPU numbers the thresholds were calibrated on.",
            ""]
    (run / "report.md").write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {run / 'results.csv'} and {run / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
