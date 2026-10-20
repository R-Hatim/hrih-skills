# Longer prose and humanizing any text

Blog and announcement posts, newsletters written as prose, case studies, one-pagers, docs and help articles, and any text someone asks you to "humanize" or "make sound less like AI".

## Contents
1. Humanizing a draft (rewrite mode)
2. Blog and announcement posts
3. Case studies and one-pagers
4. Docs and help articles
5. Final checks

## 1. Humanizing a draft (rewrite mode)

The user's draft (often AI-assisted) has real content but reads as generated. The aim is the text a skilled human editor would hand back: the same facts and argument, the writer's own quirks kept, the generated habits gone. A synonym-swapped copy with the same skeleton doesn't count.

**Process:**
1. **Read it once without editing.** Note where you'd skim, where you'd roll your eyes, and where it drones. Note what's good and specific, too: odd details, real opinions, a joke that lands, a strong verb. Those stay.
2. **List the facts and claims** the draft contains. Your version must keep every one and add none. If the draft is thin, don't fill it with invented detail. Ask for material, or mark `[NEED: …]`.
3. **Find the voice.** Use the user's sample or link if they gave one (see brand-voice.md). Without one, keep the draft's own voice where it has one, and otherwise default to plain and conversational.
4. **Run** `python scripts/check_copy.py draft.txt` and read ai-tells.md. Fix in this order:
   1. structure: preamble, recap ending, bullets that should be prose, symmetric sections
   2. patterns: contrast framing, "-ing" tails, triads, colon reveals, stock phrases
   3. words: puffery and hype, rewritten from facts
   4. rhythm, measured
5. **Run the overcorrection check** (ai-tells.md section 9) and the script again.
6. **Deliver** the rewritten text, then a short "What changed" (3–6 bullets of the main moves, not a line-by-line diff). Then any `[NEED: …]` items and anything you weren't sure about.

**Minimum effective edit.** Change what makes the text read as generated or unclear, and leave strong sentences alone. If the draft is already good, say so and make only the few edits that matter. The writer should recognize the result as their own. Keep "because", "so", "but": connectors are logic, not filler.

**What counts as a fact to keep, and what doesn't.**
- Facts are what happened: names, numbers, dates, events, decisions, results. Keep all of them.
- The generated layer is not a fact, even when it's in the draft. That includes:
  - morals ("careful planning is essential")
  - stock idioms ("slipping through the cracks")
  - significance claims ("nothing short of transformative")
  - generic advice to the reader

  Cut it, or turn it into the specific thing it gestures at, using facts that are already in the draft.
- If a lesson or opinion would make the post better but the draft doesn't contain one, ask for it in your notes ("What would you do differently next time?"). Don't write a vaguer version.

**Detector questions.** If the user's goal is to beat an AI detector, explain briefly:
- This skill makes the writing better, which tends to make it read less generated, but it promises no detector result. Detectors are noisy, and the strongest ones still flag most edited AI text.
- It won't use tricks: typos, odd characters, synonym roulette.
- Where work must be the person's own (coursework, competitions), a rewrite doesn't change who wrote it.

## 2. Blog and announcement posts

- **Open with the point or a concrete moment,** not a definition, a rhetorical question or "In today's world". The first paragraph should tell readers why this is worth their next three minutes.
- **One argument per post.** Each section moves it forward; cut sections that only restate.
- **Specifics carry the post:** real numbers, real examples, named tools, a decision and its reason, a mistake. If the user can't supply specifics, a shorter post is better than a padded one.
- **Headings** only on posts long enough to navigate (roughly 600+ words), and each heading says something ("Why we dropped the free plan").
- **End on what to do or what happens next,** or the strongest fact. Don't recap the post.
- **Announcement posts:** what's new and for whom in the first two sentences. Then how it works with one example, availability and pricing, what's next. Keep the gratitude and excitement short.

## 3. Case studies and one-pagers

- **Case study:** "[Customer] [result] with [product]", with real, approved results only. Then:
  1. a snapshot: industry, size, the key number
  2. the challenge, in their words
  3. why they chose you: the alternatives they considered
  4. how it was rolled out
  5. results with numbers
  6. a quote
  7. a CTA

  Missing pieces become `[NEED: …]`.
- **One-pager:**
  1. the value proposition
  2. the problem, in customer words
  3. how it works in 3 steps
  4. 2–4 outcomes with proof
  5. who it's for and not for
  6. one CTA with contact details

## 4. Docs and help articles

- Plain and exact beats warm and vague. Put the task in the title ("Export invoices to CSV"), the steps as a numbered list, one action per step, UI labels exactly as they appear, and the expected result after the steps.
- Cut marketing language entirely: no "seamlessly", no "powerful", no "simply". "Simply" is also unkind when the reader is stuck.
- Humanizing docs mostly means cutting: the preamble, the recap, the "It's important to note", and the restated headings.

## 5. Final checks

- [ ] The first paragraph says something specific; the last is not a recap.
- [ ] Every fact from the original is still there; nothing new was invented.
- [ ] Strong original sentences survived.
- [ ] `check_copy.py` is clean of rewrite-on-sight patterns, and paragraphs vary in rhythm.
- [ ] No second-generation tells (staccato, aphorism closers, forced casualness).
- [ ] "What changed" is short and outside the text.

## Sources

petergyang/no-ai-slop (MIT; minimum effective edit, "What changed", the writer recognizing the result); blader/humanizer (MIT; keep supported claims, add none); manavmishra/ZeroSlop (MIT; fact gate, overcorrection); stop-slop issue #42 on stripping connectors (https://github.com/hardikpandya/stop-slop/issues/42); Zinsser, *On Writing Well*; Microsoft and GOV.UK style guidance on plain task-focused docs. All paraphrased.
