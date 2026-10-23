# Working in this repo

A collection of Agent Skills (the open `SKILL.md` format). Read this before adding or changing a skill.

## Layout

```
skills/<name>/          one folder per skill; this is exactly what gets installed
  SKILL.md              frontmatter (name, description, ...) + instructions
  references/           docs the skill tells the agent to read when needed
  scripts/              helper scripts the skill runs
evals/<name>/           test prompts; kept outside the skill so installs stay lean
  evals.json            task prompts + assertions for with/without-skill runs
  trigger-eval-set.json should/shouldn't-trigger queries for tuning the description
tools/validate.py       checks every SKILL.md (run before committing)
tools/package.py        builds dist/<name>.skill for claude.ai / desktop upload
.claude-plugin/         Claude Code plugin marketplace manifest
```

## Rules for a skill

- **Folder name = `name`**: kebab-case, at most 64 characters.
- **Description** (at most 1024 chars, no `<` or `>`) is the only thing an agent sees before deciding to load the skill. It says what the skill does *and* when to use it, including phrasings that don't name the skill, and ends with when *not* to use it.
  - If the description contains `: ` (colon-space), wrap it in double quotes. Unquoted, it breaks the YAML and the skill silently fails to load.
- **Allowed frontmatter keys:** `name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility` (at most 500 chars: runtime needs such as Python or browser tools). Claude Code reads extra keys (`when_to_use`, `argument-hint`, ...), but a claude.ai upload rejects them, so keep skills to the standard keys.
- **Keep `SKILL.md` under about 500 lines.** Push detail into `references/` and point to it from `SKILL.md`, saying when to read it.
- **Explain why, not just what.** Agents follow reasoning better than all-caps rules.
- **Scripts:**
  - Portable (Windows, macOS, Linux), standard library only where possible.
  - Runnable as `python scripts/x.py` and under `python -I`.
  - They print where their outputs went.
- **No secrets, personal paths or machine-specific values** anywhere in `skills/`.
- **Shared files are copies.** Each skill installs on its own, so the review skills each carry `scripts/lessons.py`, `scripts/diff_facts.py` and `references/lessons.md`. Edit one copy, then copy it to the others; `tools/validate.py` fails when they drift.

## Before committing

```bash
python tools/validate.py
claude plugin validate .  # checks .claude-plugin/marketplace.json
python tools/package.py   # optional, output is gitignored
```

When a skill changes, **bump its `version` in `.claude-plugin/marketplace.json`**. Claude Code users only receive an update when that version changes. The marketplace name `hrih-skills` is what users type in install commands, so don't rename it casually. Names like `agent-skills` and `anthropic-*` are reserved.

For claude.ai users, attach the `dist/*.skill` files to a GitHub Release.

## Testing a skill

1. Run each prompt in `evals/<name>/evals.json` twice: once with the skill and once without, as fresh agents.
2. Grade the outputs against the assertions and look at them yourself. Design and writing quality need human eyes.
3. Keep runs in a `<name>-workspace/` folder outside `skills/`; it's gitignored.
4. For the description, use `trigger-eval-set.json` with skill-creator's `run_loop`, choosing by held-out score, not train score.
   - On Windows, its `run_eval.py` needs a non-`select()` pipe reader.
   - Its parallel workers can pick each other's temporary command, so count any copy of the skill as a trigger.

## Adding a skill

1. Create `skills/<name>/SKILL.md` (copy an existing skill's structure).
2. Add `evals/<name>/evals.json` with 2–3 realistic prompts.
3. Add the skill to `.claude-plugin/marketplace.json` and to the table in `README.md`.
4. Run `tools/validate.py`.
