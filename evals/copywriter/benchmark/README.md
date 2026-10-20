# copywriter: AI-detector benchmark

A small, reproducible check of whether the skill's output reads less machine-like than plain Claude output. It compares three things on the same briefs:

- **H**: human-written marketing copy archived on the Wayback Machine no later than 2019-12-31. Copy.ai and Jasper launched in 2020–21, so earlier copy is very unlikely to be AI-written.
- **A**: Claude without the skill.
- **B**: Claude with the skill.

The detector is **one signal next to human review, not the goal**. The skill is not tuned against it, and it contains no detector-evasion tricks.

## Why Binoculars, and what it can't tell you

- **Watermark detectors can't judge this.** Google SynthID, OpenAI's and Anthropic's detectors only recognize their own provider's watermark, and A and B would carry the same one.
- **Commercial classifiers** (Pangram has the best independent record) need an account and paid API credits.
- **Binoculars** (Hans et al., ICML 2024) is open, zero-shot and runs locally:
  - It compares how surprising a text is to Falcon-7B-instruct with how surprising Falcon-7B expects it to be.
  - Lower scores look more machine-written.
  - Published thresholds: 0.8536 (low false-positive mode), 0.9015 (accuracy mode).
- **Known limits:**
  - It has been weak on Claude text in some studies.
  - It can wrongly flag plain, formulaic or famous human text, which is why H's flag rate is part of the result.
  - Marketing copy is outside every validated detector domain.

The stylometrics table (sentence-length spread, dash and contraction rates, triads, watch words, rewrite-level findings from `check_copy.py`) is descriptive, not a detector. It shows *what* changed between A and B, compared with real human copy.

## Files

| File | What it does |
|---|---|
| `briefs.json` | One brief per human control, built only from facts in that control (no phrasing) |
| `manifest.json` | Each control's Wayback URL, timestamp, start and end anchors, and SHA-256, plus the selection notes. Human texts themselves are not published (copyright) |
| `fetch_controls.py` | Rebuilds the human texts from the Wayback Machine using the manifest, and checks their hashes. Optional item ids retry single items, since Wayback is slow |

**The control set:**
- 10 pieces of small-business copy archived in 2018–2019: 2 website sections, 3 marketing emails, 2 blog posts and 3 product descriptions, each 140–370 words.
- Companies were taken in index order from a walk of archived Mailchimp campaign pages, which is effectively random. The skips, and the reason for each, are logged in `manifest.json`.
- Famous brands were excluded on purpose: memorized text scores as machine-written.
| `generate.py` | Runs `claude -p` for A (skills disabled) and B (`/copywriter <brief>`), N samples each |
| `normalize.py` | Strips assistant scaffolding (preambles, notes, unit labels, `[NEED]` placeholders) and Markdown the same way for every text, then computes stylometrics |
| `binoculars_score.py` | Scores every normalized text with Binoculars, loading one 7B model at a time (runs on a 64 GB machine without a big GPU) |
| `report.py` | Writes `results.csv` and `report.md`: scores by condition with brief-level bootstrap intervals, flag rates, separability from human copy (AUROC), paired B-minus-A differences, and stylometrics |

## Run it

```bash
# 1. Human controls (stdlib; downloads 10 archived pages; add item ids to retry single items)
python -I fetch_controls.py manifest.json RUN/human

# 2. Generate A and B (needs the claude CLI, logged in; about 15 minutes for 10 briefs x 2 samples x 2 conditions)
python generate.py --briefs briefs.json --skill ../../../skills/copywriter --out RUN --samples 2

# 3. Normalize and compute stylometrics
python normalize.py --run RUN --human RUN/human --skill ../../../skills/copywriter

# 4. Binoculars (needs: pip install torch transformers accelerate safetensors; ~29 GB of model downloads)
python binoculars_score.py RUN/normalized -o RUN/binoculars.json

# 5. Report
python report.py --run RUN
```

Binoculars on CPU takes about 1-2 minutes per text (about 1.5 hours for 50 texts), so run it overnight. In bfloat16 each model needs about 15 GB of RAM. float32 needs about 30 GB, and Windows may refuse it with "paging file too small".

## Reading the results

- Expect plain Claude output (A) to be flagged often, and don't expect the skill to flip that. Pattern-removal skills barely move strong detectors.
- The informative numbers are:
  - **separability from H** (AUROC: closer to 0.5 means harder to tell apart)
  - the **paired B-minus-A difference** per brief
  - **H's own flag rate**, the detector's false-positive rate on this kind of copy
- With 10 briefs, only large effects are detectable. If no human control is flagged out of 10, the false-positive rate could still be as high as about 30%.
- A lower detector score is never evidence that copy is better. Read the texts.

## Results, 2026-10-20 (copywriter 1.0.0, Claude Opus 5.5)

10 briefs and 50 texts. Binoculars ran in bfloat16 on CPU.

| | Human (2018–19) | Claude, no skill | Claude + skill |
|---|---|---|---|
| Binoculars mean (95% CI by brief) | 1.008 (0.983–1.035) | 0.966 (0.948–0.984) | 0.979 (0.965–0.993) |
| Flagged as AI (either threshold) | 0/10 | 0/20 | 0/20 |
| Separability from human copy (AUROC) | | 0.78 (0.67–0.89) | 0.71 (0.53–0.89) |
| Em dashes / 100 words | 0.08 | 0.06 | 0.00 |
| Lists of three / 100 words | 0.82 | 0.99 | 0.81 |

- **No text was flagged at the published thresholds.** Binoculars can't catch this model's copy as a pass/fail detector.
- **Its continuous score still separates human from Claude copy moderately.**
- **With the skill, the copy moved toward the human controls**: higher on 7 of 10 briefs, mean +0.013, 95% CI −0.002 to +0.028. That's suggestive at this sample size, not conclusive.
- **Where the skill helped most in testing** was rewriting AI drafts and not inventing facts, which this benchmark doesn't measure. Read the texts too.
