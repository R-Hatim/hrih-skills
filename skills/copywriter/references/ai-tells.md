# AI-writing tells: catalog and fixes

Use this in the editing passes, after a draft exists. Don't read it as a list of words to avoid while drafting. Writing *toward* specifics (SKILL.md step 3) prevents most of these. Writing *away* from banned words only produces synonyms.

## Contents
1. How to use this catalog
2. Structural patterns (the most persistent tells)
3. Rhythm and shape
4. Words (a watch list, not a ban list)
5. Tone and stance
6. Content
7. Formatting
8. Chat leftovers (zero tolerance)
9. Second-generation tells and overcorrection
10. Not reliable tells (don't "fix" these)
11. Other languages
12. Sources and credits

## 1. How to use this catalog

- **Tells cluster.** One list of three or one dash proves nothing; humans use every device here. What readers notice is the same move repeated, or several moves stacked in one paragraph. Act on density and repetition.
- **Structure beats vocabulary.** Word habits change with every model generation: "delve" was everywhere in 2024 and is rare now. The structural habits (contrast framing, "-ing" tails, reflexive triads, flat rhythm, generic claims) have stayed stable across models and vendors. Spend your effort there.
- **Fix from the facts.** The fix for a tell is almost never a synonym. Ask what the sentence is trying to claim, find the fact that would make a reader believe it, and write that. If there is no fact, cut the sentence or mark `[NEED: …]`.
- **Marketing may sell.** Encyclopedic style guides treat all promotional language as a fault. Copy is allowed to persuade; the target is *empty* persuasion (adjectives standing in for facts), not persuasion itself.
- **Severity levels used below:**
  - **Rewrite**: fix every instance (narrow exceptions are listed).
  - **Cap**: fine occasionally; the default limit is given.
  - **Watch**: only a problem in clusters or repeated.
  - **Strip**: never belongs in delivered copy.

`scripts/check_copy.py` finds most of the patterns in sections 2, 3, 7 and 8 mechanically. Sections 4–6 and 9 need judgment.

## 2. Structural patterns

### Contrast framing: **Rewrite**
"It's not X, it's Y." "Not just X, but Y." "This isn't about X. It's about Y." "Less X, more Y." "X, not Y" as a headline formula.
- *Why it reads as AI:* it manufactures a debate with a view nobody stated, in order to sound insightful. It is the single most persistent tell in 2025–2026 studies (it appeared in about 6% of ChatGPT replies in mid-2025 and nearly tripled on the web since 2023).
- *Exception:* the reader really does hold the rejected view, and saying so helps them. At most once per piece.
- *Fix:* state the positive claim and support it.
  - Before: *It's not just a calendar. It's a whole new way to own your time.*
  - After: *Slate blocks two hours of focus time each morning and declines meetings that land on it.*

### Negation lists: **Rewrite**
"No setup. No contracts. Just results." "No X, no Y, no Z."
- *Exception:* one plain statement of absence next to a CTA when it answers a real objection ("No card required").
- *Fix:* say what *does* happen.
  - Before: *No spreadsheets. No chasing. Just paid invoices.*
  - After: *Invoices go out when a job is marked done, and clients get a reminder on day 7 and day 14.*

### "-ing" significance tails: **Rewrite**
"…, ensuring a smooth experience." "…, highlighting our commitment to quality." "…, making it easier than ever to…" "…, fostering collaboration."
- *Why:* a cheap way to attach an evaluation to a fact. Measured at about 5× the human rate in instruction-tuned models.
- *Fix:* cut the tail. If it held a real consequence, give that its own sentence with a concrete subject.
  - Before: *We added offline mode, ensuring you stay productive wherever you are.*
  - After: *Offline mode keeps your last 30 days of notes on the phone. Edits sync when you're back online.*

### Self-answered questions and colon reveals: **Rewrite** (in body copy)
"The result? Happier customers." "The best part? It's free." "Here's why:" "The secret: consistency."
- *Exception:* FAQ entries, and a question the reader is actually asking (in their words) as a headline.
- *Fix:* give the answer as a statement, with the fact that makes it interesting.
  - Before: *The best part? You don't need a developer.*
  - After: *You can install it without a developer: paste one line into your site's header.*

### "Whether you're X or Y" and false ranges: **Rewrite**
"Whether you're a seasoned pro or just getting started…" "From startups to enterprises…" "Everything from budgeting to big dreams."
- *Why:* addresses everyone, commits to no one.
- *Fix:* name the actual reader, or give each real segment its own sentence and reason.
  - Before: *From solo founders to Fortune 500 teams, Pathline powers growth at every scale.*
  - After: *Most Pathline customers are agencies with 5 to 40 people.* (only if true)

### Stock openers and closers: **Rewrite**
- Openers: "In today's fast-paced world", "In an era where", "ever-evolving landscape", "When it comes to", "It's no secret that", "Let's dive in", "Let's break it down", "Here's the thing", "Here's what you need to know", "Look no further", "Imagine a world where", "Say goodbye to".
- Closers: "In conclusion", "Ultimately,", "At the end of the day", "The bottom line", "And that changes everything", "Ready to take X to the next level?", "So what are you waiting for?".
- *Fix:* delete. The first sentence should contain content. The last should be a fact or the next action.

### "Serves as / stands as / boasts / represents": **Rewrite**
- *Why:* models upgrade "is" and "has" to sound grander. Plain copulas are invisible, which is the point.
- Before: *The Pro plan boasts unlimited projects and serves as the ideal choice for growing teams.*
- After: *Pro has unlimited projects. Most teams move to it after their fourth.* (second sentence only if true)

### Decorative lists of three: **Cap** (one per section)
"Fast, simple, and secure." "For teams, for creators, and for enterprises." Three bullets under every heading.
- *Why:* triads sound complete, so models reach for them whether or not there are three things. Measured at about 4× the human rate.
- *What the cap is for:* decorative triads such as adjective trios, slogan trios and benefit trios. A list of three genuinely different things (three services, three steps, three plans, three features the brief names) is just a list: write it as one, in one sentence if it reads naturally.
- *Don't dodge the cap by splitting.* Breaking a real list into separate sentences ("We map your stakeholders. Then we build your strategy. Then we support…") swaps one tic for another.
- *Fix:* make each list its natural length, and drop items that are synonyms of each other ("simple, easy and intuitive" is one item).
  - Before: *Built for speed, designed for simplicity, and engineered for scale.*
  - After: *Pages render in 80 ms on a mid-range phone.*

### Em dashes: **Cap**
- *Why it matters for this skill:* in a 2026 comparison of major models, only Claude still used more em dashes than professional writers. Vendor data puts Claude at roughly 7× the human rate.
- *Limits:*
  - None in very short copy (headlines, subject lines, ads, buttons).
  - In body copy, about one per 300–500 words, and never as the default way to set up a punchline ("It's fast — really fast.").
- *Don't strip them mechanically.* Text reduced to commas and periods is its own newer pattern. Pick the mark that fits:
  - a comma for an aside
  - a colon for an explanation or list
  - a period for a real pivot
  - parentheses for a true aside
  - a dash only where nothing else works
- *A voice sample overrides this.* If the writer's own text uses dashes at some rate, match roughly that rate.

### Fragments and staccato: **Cap** (one per section)
"Faster. Smarter. Simpler." One-line paragraphs for drama. "It's time to… It's time to…"
- *Fix:* keep a fragment only when it carries a fact. Merge the rest into one sentence with content.
  - Before: *Less clutter. More clarity. Total control.*
  - After: *Hide the columns you don't use, and the table remembers your layout on every device.*

### Rhetorical questions: **Cap** (one per piece, outside FAQs)

### Stacked transitions: **Cap**
Sentences opening with Additionally, Moreover, Furthermore, Notably, Importantly. One is fine. A paragraph of them reads as a template.
- *Fix:* delete the transition. If the paragraph no longer follows, reorder the content instead of gluing it.

### "And"-chained sentences with light punctuation: **Watch**
Long sentences joined by "and…and…and", with no semicolons, parentheses or quoted voices. A 2026 study found this is now one of the clearer signs as models shed dashes.
- *Fix:* split by meaning. Let a real aside go in parentheses. Quote a real customer where you have one.

## 3. Rhythm and shape

### Flat sentence length: **Rewrite** when a whole paragraph is flat
Every sentence lands at 14–22 words with the same subject–verb–object shape. Read aloud, it drones.
- *Why prompting doesn't fix it:* telling a model to vary rhythm moves it unpredictably, and examples of human rhythm can make it flatter (NeurIPS 2026). So measure after drafting: `check_copy.py` reports length spread per paragraph.
- *Fix:* restructure by meaning, not by alternation.
  - Give the key fact its own short sentence.
  - Let the mechanism or story run long.
  - Merge two thin sentences.

  Before: *Our scheduling tool helps teams coordinate meetings more efficiently. It integrates with popular calendar applications seamlessly. It also provides analytics to help you understand time usage.*

  After: *Pick a time once. Slate checks all six calendars, finds the next slot everyone has free and sends the invite before you've closed the tab. On Fridays it tells you how many hours went to meetings.*

### Blocky paragraphs and symmetric sections: **Rewrite**
Every paragraph 3–4 sentences, every feature card the same shape, every section the same length, pros and cons perfectly balanced.
- *Fix:* weight by importance to the reader. Give the feature buyers ask about a full paragraph with proof, and put the minor ones in one line.

### A punchline at the end of every paragraph: **Cap** (one memorable line per piece)
"…because great work deserves great tools." "…and that's the power of simplicity."
- *Fix:* end ordinary paragraphs on a fact: *"…and the export is a plain CSV your accountant can open."*

## 4. Words (a watch list, not a ban list)

These words are fine in the right sentence. They're a problem when they replace a fact, or when two or three cluster in a paragraph. **Never fix them with a synonym** ("harness" for "leverage" is the same sentence). Ask what the word claims and write that claim, or cut it.

| Family | Examples | What to write instead |
|---|---|---|
| Significance puffery | testament to, pivotal/crucial/vital role, marks a turning point, sets the stage, underscores the importance | The consequence for the reader, or nothing |
| Hype verbs | unlock, unleash, elevate, empower, supercharge, revolutionize, transform, streamline, harness, leverage | What the product physically does and the measurable result |
| Empty adjectives | seamless, robust, cutting-edge, innovative, next-level, world-class, best-in-class, effortless, powerful, intuitive | The evidence that would make a reader use the adjective themselves |
| Grand abstract nouns | landscape, realm, journey, ecosystem, tapestry, paradigm, synergy, beacon, cornerstone | The actual market, customers, tools or steps |
| Magic adverbs | truly, genuinely, deeply, incredibly, seamlessly, effortlessly, quietly, notably, significantly | Delete. If the sentence collapses, it needed evidence, not emphasis |
| Brochure register | nestled, vibrant, renowned, rich heritage, a diverse array of, commitment to excellence | Concrete sensory or factual detail |
| Stiff verbs and hidden verbs | utilize, facilitate, commence, conduct an analysis of, the implementation of | use, help, start, analyze, implement |
| Era-specific (2023–2025, fading) | delve, intricate, meticulous, showcase, underscore, foster, interplay, multifaceted | Plain words. Their absence proves nothing |

**Synonym cycling** (Watch): one product called "the app", "the platform", "the solution" and "this powerful tool" in four sentences. Pick one name and repeat it. Repetition reads as human; a thesaurus doesn't.

## 5. Tone and stance

- **Flattery and eager openers** (Strip in copy): "Great question!", "Absolutely!". In FAQs and support copy, answer first.
- **Generic hedges** (Rewrite): "It's important to note", "Keep in mind", "Results may vary". Either say the thing or make the hedge specific: *"Battery lasts about 9 hours of video, or two days of light use."*
- **Vague attribution** (Rewrite): "Studies show", "Experts agree", "Many customers say". Name the source and date, or cut it.
- **Both-sidesing** (Rewrite): "It depends on your needs", "There's no one-size-fits-all". Brands need a position. Say who it's for and who it isn't: *"If you have fewer than five people, a spreadsheet is fine. We're for teams that outgrew one."*
- **Inflated stakes** (Rewrite): "redefine what's possible", "the future of X is here". Scale the claim to the actual change.
- **Uniform enthusiasm** (Watch): every feature "amazing", exclamation marks, no trade-off anywhere. Admit one real limitation; it makes everything else more believable. No exclamation marks in body copy unless the voice is genuinely like that.
- **Faux intimacy** (Watch): "Let's be honest…", "We've all been there…", "Think of it as…". Give the concrete scenario instead.

## 6. Content (what readers feel without spotting a pattern)

- **Generic claims** (Rewrite): sentences a competitor could publish unchanged. Run the *swap test*: replace the brand name with a competitor's; if it's still true, it says nothing.
- **No specifics** (Rewrite): no numbers, names, places, dates, versions or constraints. Every claim-bearing sentence gets one, taken from the proof inventory.
- **Invented proof** (Strip): plausible stats ("boost productivity by 47%"), "trusted by thousands", made-up testimonials and personas ("Dr. Sarah Chen, Head of Innovation"). Use real proof or a `[NEED: …]` placeholder.
- **Benefits with no mechanism** (Rewrite): "enhances collaboration", "drives efficiency". Show what's on the screen: *"Type @ and a name; they get that paragraph, not the whole doc."*
- **Padding** (Rewrite): restating the question, explaining why a benefit is good ("saving time matters because time is valuable"), saying each point three times. Say it once, where it's most useful. Cutting 20–30% usually loses nothing.
- **Generic morals and lessons** (Rewrite): "careful planning is essential", "the right tool can make all the difference", "communication is key". They sound like a conclusion and say nothing, and rewording one ("the big lesson is that a migration needs careful planning") keeps the padding. Cut it, or replace it with the specific lesson if the user can give you one ("Next time we'd export the old threads before switching"). Never invent the lesson.
- **Stock idioms** (Watch): "slipping through the cracks", "move the needle", "low-hanging fruit", "peace of mind", "hit the ground running", "a no-brainer". One can be the writer's voice. In an AI draft they're filler: name what actually happened ("emails sat unanswered for days").
- **Coined labels** (Watch): "workflow debt" or "the productivity paradox gap" presented as established terms. Describe the thing plainly unless the brand deliberately owns the term.

## 7. Formatting

- **Markdown where it won't render** (Strip): literal `**`, `##`, `---` in email, SMS, CMS fields, app stores and social posts.
- **Bullets for non-list content** (Rewrite): arguments and value propositions belong in prose. Lists are for steps, specs and comparisons.
- **Bold-label bullets** (Rewrite): "**Speed:** Lightning-fast performance." Write each item as a specific sentence; drop labels that repeat the item.
- **Emoji as structure** (Strip): ✅ 🚀 ✨ 💡 at the start of lines or headings. Use emoji only where the channel and voice call for it, mid-sentence the way people do.
- **Title Case Headings** (Watch): follow the house style; sentence case is the safer default on the web.
- **Over-bolding** (Cap): at most one bold phrase per screen, for something a scanner needs (a price, a deadline).
- **Unusual characters** (Strip): →, ✓, fancy bullets, non-breaking or zero-width spaces in plain text. Use what a person would type.

## 8. Chat leftovers (Strip, zero tolerance)

- "Here's a revised version", "Sure!", "I hope this helps", "Let me know if you'd like…", "Feel free to adjust".
- "As an AI…", "As of my last update…", "While specific details are limited…".
- Unfilled template brackets: [Company Name], {product}, INSERT_URL, XX%, lorem ipsum. Your own `[NEED: …]` placeholders are deliberate; they go in the notes list and must be resolved before publishing.
- Citation or tool residue: `oaicite`, `contentReference`, `turn0search0`, `[cite: 1]`, `utm_source=chatgpt.com`.
- Process narration inside the deliverable: *"This version keeps the friendly tone while…"*. That belongs in the notes.

## 9. Second-generation tells and overcorrection

Removing first-order tells tends to produce new ones. In one public test of a popular humanizer, its rewrites cut listed AI words from 70 to 0, while uniform sentence rhythm rose from 60 to 101 and aphoristic closers from 38 to 61. After any rewrite, check for:

- **Staccato bursts**: choppy fragments replacing every long sentence ("broetry").
- **Wisdom-shaped closers**: an epigram ending each paragraph.
- **Perfect balance**: sections, bullets and sentences all the same size.
- **Performed voice**: forced casualness, slang, edginess, "Look,", fake candor, invented anecdotes or experiences.
- **Reflexive specificity**: suspiciously round or suspiciously exact numbers with no source.
- **Stripped logic**: "because", "so", "but", "which means" deleted until the argument becomes disconnected claims.
- **New tics from repeated fixes**: the same replacement pattern applied everywhere (every paragraph now opens with a short declarative, every dash became a colon).
- **Commas-and-periods-only punctuation**: dashes, semicolons and parentheses all gone.

The fix is the same as before: go back to the facts, size sentences by meaning, keep the connectors, and stop editing lines that already work.

## 10. Not reliable tells (don't "fix" these)

Over-correcting makes copy worse and flattens real voices.

| Feature | Why it isn't evidence |
|---|---|
| A single em dash | A long-standing human device. Density and the dash-as-pivot habit are the signal |
| Curly quotes, correct grammar, polish | Word processors and good writers produce them |
| Transition words on their own (however, so, because) | Normal connective tissue. Only stacks of sentence-initial ones read as templates |
| One triad, one contrast, one rhetorical question | Classical rhetoric. The tell is doing it in every paragraph |
| Lists for list-shaped content | Specs, steps and plan comparisons belong in lists |
| Formal vocabulary in general; British or American spelling; contractions or their absence | Style and register choices |
| Non-native patterns (formal register, synonym variety) | Taught in many school systems; don't treat a person's English as a tell |
| The word "delve" | Already rare in current models; its absence proves nothing |
| An AI-detector score | Error-prone, model-specific, and biased against plain and non-native writing. Never the goal |

## 11. Other languages

- The **structural** tells transfer:
  - contrast framing, "-ing"-style tails (as participles or gerunds)
  - reflexive triads, flat rhythm
  - generic claims, recap endings
  - bullet-itis

  Check for them in any language.
- **English word lists don't transfer.** Each language has its own stock phrases, often calqued from English:
  - German: "Es ist wichtig zu beachten", "Tauchen wir ein", "Zusammenfassend lässt sich sagen", heavy "nicht nur … sondern auch".
  - French: "Il est important de noter", "plonger dans", "dans un monde en constante évolution".

  Treat calques of English marketing buzzwords as a tell.
- **Use native typography.**
  - Quotation marks: German „…" or »…«; French « … »; Slovenian „…" or »…«.
  - Dashes: German and Slovenian use a spaced en dash ( – ) as the dash. In French the em dash is normal dialogue punctuation, so native use isn't a tell.
  - Headings in sentence case (title case is an English convention).
- **Write natively.** Draft in the target language from the facts, rather than translating an English draft sentence by sentence.
- `check_copy.py --lang xx` keeps the language-neutral checks (rhythm, punctuation density, formatting, leftovers) and skips English phrase patterns.
- For languages without published studies (e.g. Slovenian), the checks above are editor heuristics. A native speaker's read is the reliable final pass.

## 12. Sources and credits

Evidence for the patterns and rates above:
- Kobak et al., "Delving into LLM-assisted writing in biomedical publications through excess vocabulary", *Science Advances* 2025 (https://arxiv.org/abs/2406.07016).
- Reinhart et al., "Do LLMs write like humans?", *PNAS* 2025 (https://arxiv.org/abs/2410.16107): participial clauses and nominalizations.
- Liang et al., 2024 (https://arxiv.org/abs/2404.01268).
- Juzek & Ward, COLING 2025 (https://arxiv.org/abs/2412.11385).
- Russell, Karpinska & Iyyer, ACL 2025 (https://arxiv.org/abs/2501.15654): what expert readers notice.
- Lanzo & Angelo, "Burstiness Was Measured Wrong, and Prompting Cannot Aim It", NeurIPS 2026 (https://neurips.cc/virtual/2026/164820).
- Paech et al., "Antislop", 2025 (https://arxiv.org/abs/2510.15061).
- Pew Research Center, "How Much of the Internet Is Written With AI?", 2026-08-20 (https://www.pewresearch.org/data-labs/2026/08/20/how-much-of-the-internet-is-written-with-ai/).
- The Washington Post's analysis of ChatGPT messages, Nov 2025.
- The Economist's 2026 punctuation study.
- Pangram, "Signs of AI writing" (https://www.pangram.com/signs-of-ai-writing).

Field guides and skills whose ideas are adapted here, in our own words:
- Wikipedia, "Signs of AI writing", WikiProject AI Cleanup, CC BY-SA 4.0 (https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing): taxonomy, caveats, ineffective indicators.
- coreyhaines31/marketingskills, MIT (https://github.com/coreyhaines31/marketingskills): rewrite-vs-cap severity, second-generation tells, `[NEED: …]` placeholders, the swap test.
- blader/humanizer, MIT (https://github.com/blader/humanizer): grouping tells by cause, voice samples overriding rules, the humanizer test cited in section 9.
- conorbronsdon/avoid-ai-writing, MIT (https://github.com/conorbronsdon/avoid-ai-writing): density over presence, explicit exceptions.
- petergyang/no-ai-slop, MIT (https://github.com/petergyang/no-ai-slop): minimum effective edit, "the writer would recognize it".
- manavmishra/ZeroSlop, MIT (https://github.com/manavmishra/ZeroSlop): overcorrection catalog.

Editing tradition: Orwell, "Politics and the English Language" (1946); Strunk, *The Elements of Style* (1920); Zinsser, *On Writing Well*; Hopkins, *Scientific Advertising* (1923); digital.gov plain-language guidance.
