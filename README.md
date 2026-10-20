# hrih-skills

A collection of [Agent Skills](https://agentskills.io): folders of instructions and scripts that teach AI agents to do specific jobs well. Skills use the open `SKILL.md` format, so they work in Claude Code, claude.ai, and the many other agents that support it (Codex, Cursor, GitHub Copilot, Gemini CLI, OpenCode, Amp, Goose and more).

## Skills

| Skill | What it does | Needs |
|---|---|---|
| [design-inspiration](skills/design-inspiration/SKILL.md) | Before designing a website, landing page, email, pitch deck, social post or ad, it researches current work in curated galleries, picks the best references for the brief across varied styles and palettes, extracts their real fonts, colors and layouts, writes a design direction, then builds and checks the result against the references. | A browser tool (or WebFetch); Python 3.10+; Chrome, Chromium or Edge for screenshots |

## Install

### Claude Code (plugin marketplace)

```text
/plugin marketplace add R-Hatim/hrih-skills
/plugin install design-inspiration@hrih-skills
```

To get updates later, run `/plugin marketplace update hrih-skills`, then update the plugin from `/plugin`. You can also turn on auto-update for this marketplace in `/plugin` > Marketplaces.

### Any agent, with the `skills` CLI

[`npx skills`](https://github.com/vercel-labs/skills) detects the agents you have installed (Claude Code, Codex, Cursor, Copilot, Gemini CLI, OpenCode, Amp, Goose and more) and installs into each:

```bash
npx skills add R-Hatim/hrih-skills
```

Useful flags:
- `--skill design-inspiration` installs one skill.
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

1. Download `design-inspiration.skill` from this repo's [Releases](../../releases), or build it with `python tools/package.py`, which writes to `dist/`.
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

## License

[MIT](LICENSE)
