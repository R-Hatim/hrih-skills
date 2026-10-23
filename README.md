# hrih-skills

A collection of [Agent Skills](https://agentskills.io): folders of instructions and scripts that teach AI agents to do specific jobs well. Skills use the open `SKILL.md` format, so they work in Claude Code, claude.ai, and the many other agents that support it (Codex, Cursor, GitHub Copilot, Gemini CLI, OpenCode, Amp, Goose and more).

How the skills work, with before/after examples and a detector benchmark: **[hrih.si/projects/hrih-skills](https://hrih.si/projects/hrih-skills/)**.

## Skills

| Skill | What it does | Needs |
|---|---|---|
| [design-inspiration](skills/design-inspiration/SKILL.md) | Before designing a website, landing page, email, pitch deck, social post or ad, it researches current work in curated galleries, picks the best references for the brief across varied styles and palettes, extracts their real fonts, colors and layouts, writes a design direction, then builds and checks the result against the references. | A browser tool (or WebFetch); Python 3.10+; Chrome, Chromium or Edge for screenshots |
| [copywriter](skills/copywriter/SKILL.md) | Writes and rewrites website, email, ad, social, UX and blog copy. It starts from facts and the customer's own words, drafts, then edits in passes against an evidence-based catalog of AI-writing tells (contrast framing, "-ing" tails, reflexive triads, flat rhythm, puffery). It also humanizes AI drafts and matches a voice from a sample or a link. It never invents stats or testimonials and uses no detector-evasion tricks. | Nothing required; Python 3.8+ for its linter and page-text scripts |
| [review-router](skills/review-router/SKILL.md) | Decides how much human review a change needs, from the change rather than its author: a fixed floor of sensitive paths, judgement about intent, blast radius and reversibility above it, every risk paired with the check that covers it, and the three hunks a human should read first. Learns from human overrides. | git, Python 3.9+ |
| [review-apprentice](skills/review-apprentice/SKILL.md) | Code review as teaching when an AI reviews too. The junior reviews first without seeing the AI's findings, then judges each AI finding with a reason; a senior checks those calls, and their corrections become lessons the next person reads. | git, Python 3.9+ |
| [spec-review](skills/spec-review/SKILL.md) | Reviews a change against its spec and its evidence instead of every line: testable criteria for the human to confirm, acceptance checks written from the spec rather than the code, tests mapped to real output, a mutation pass over the changed lines, and a check for tests bent to fit the code. | git, Python 3.9+, the project's test command |

The three review skills share one memory, `REVIEW-LESSONS.md`: what the people on a project have taught the reviewers, in their own words, read from the base branch so a change can't rewrite its own review. Its format and rules are in [references/lessons.md](skills/review-router/references/lessons.md).

Why these three exist, and what about 70 agent reviews with and without them showed: **[Who teaches the reviewer?](https://hrih.si/articles/who-teaches-the-reviewer/)**

## Install

### Claude Code (plugin marketplace)

```text
/plugin marketplace add R-Hatim/hrih-skills
/plugin install design-inspiration@hrih-skills
/plugin install copywriter@hrih-skills
/plugin install review-loop@hrih-skills
```

To get updates later, run `/plugin marketplace update hrih-skills`, then update the plugin from `/plugin`. You can also turn on auto-update for this marketplace in `/plugin` > Marketplaces.

### Any agent, with the `skills` CLI

[`npx skills`](https://github.com/vercel-labs/skills) detects the agents you have installed (Claude Code, Codex, Cursor, Copilot, Gemini CLI, OpenCode, Amp, Goose and more) and installs into each:

```bash
npx skills add R-Hatim/hrih-skills
```

Useful flags:
- `--skill copywriter` installs one skill.
- `-g` installs for your user instead of the current project.
- `-a claude-code -a codex` targets specific agents.
- `--copy` copies instead of symlinking, for systems without symlink support.

With the GitHub CLI (preview), you can instead run `gh skill install R-Hatim/hrih-skills design-inspiration`.

### Manually

Copy the skill folder to wherever your agent loads skills from:

| Agent | User-level folder |
|---|---|
| Claude Code | `~/.claude/skills/` |
| Codex, Cursor, Copilot, Gemini CLI, OpenCode, Amp, Goose | `~/.agents/skills/` |

```bash
git clone https://github.com/R-Hatim/hrih-skills
cp -r hrih-skills/skills/design-inspiration ~/.claude/skills/
```

On Windows (PowerShell):

```powershell
git clone https://github.com/R-Hatim/hrih-skills
Copy-Item -Recurse hrih-skills\skills\design-inspiration "$env:USERPROFILE\.claude\skills\"
```

For a single project, use `.claude/skills/` or `.agents/skills/` inside that repo instead.

### claude.ai and the Claude desktop app

1. Download a skill file (e.g. `copywriter.skill`) from this repo's [Releases](../../releases), or build it with `python tools/package.py`, which writes to `dist/`.
2. In Claude, turn on code execution: Settings > Capabilities.
3. Go to Customize > Skills > **+** > Create skill > **Upload a skill**, and choose the file.

## Repo layout

```
skills/<name>/       the skill itself; this folder is what gets installed
evals/<name>/        test prompts used to evaluate the skill and tune its description
tools/validate.py    checks every SKILL.md against the spec
tools/package.py     builds uploadable .skill files into dist/
.claude-plugin/      Claude Code marketplace manifest
```

Contributing or building a new skill: see [AGENTS.md](AGENTS.md).

## Notes

- `design-inspiration` browses public pages of land-book.com, supahero.io, pricingpages.design, socialproofexamples.com, navbar.gallery, ogimage.gallery, reallygoodemails.com, deck.gallery, posts.design and adfolio.design. It uses them as visual reference only, borrows patterns rather than assets, never signs in, and doesn't get around bot protection. This project isn't affiliated with any of those sites.
- `copywriter` aims at better writing, not at fooling detectors. Its tells catalog adapts ideas from [blader/humanizer](https://github.com/blader/humanizer), [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills), [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing), [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop) and [manavmishra/ZeroSlop](https://github.com/manavmishra/ZeroSlop) (all MIT) and Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), rewritten in our own words. Sources are listed in the skill's references. `evals/copywriter/benchmark/` has a reproducible AI-detector benchmark (Binoculars plus stylometrics against pre-2020 human copy).

## License

[MIT](LICENSE)
