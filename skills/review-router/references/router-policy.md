# Tuning the floor: `.review/policy.json`

`scripts/diff_facts.py` ships with default categories that set a minimum review tier. A repo can tune them with `.review/policy.json`. Like the lessons file, it's read from the **base branch**, so a change can't relax the rules it's judged by. Editing the policy is itself a `review-config` change that needs a human.

## Shape

```json
{
  "large_change_lines": 400,
  "huge_change_lines": 1000,
  "categories": {
    "payments": { "tier": "high", "words": ["payment", "billing", "invoice", "ledger", "payout"] },
    "billing-ui": { "tier": "medium", "why": "shows prices to customers", "globs": ["web/src/pricing/**"] },
    "public-api": null
  }
}
```

- A category you name replaces the default with the same name, field by field; `null` removes a default category.
- `tier`: `low`, `medium` or `high`, the minimum for any change touching a match.
- `globs`: whole-path patterns. `*` stays inside one folder, `**` crosses folders.
- `words`: whole words in any path segment. camelCase and snake_case are split first, so `accessToken.ts` matches `token` but `tokenizer.py` doesn't.
- `human: true`: a human must approve any change touching a match, whatever the tier. The defaults set it for CI workflows and for files that instruct reviewers and agents (`REVIEW-LESSONS.md`, `.review/`, `CODEOWNERS`, `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.cursor/`).
- `why`: one line shown in the report.
- `large_change_lines`: above this many changed lines (excluding lockfiles and generated files) the floor is at least medium. `huge_change_lines`: above this, the report suggests splitting the change.

## Defaults and the thinking behind them

| Category | Floor | Why |
|---|---|---|
| review-config | high, human | Files that tell reviewers and agents what to do are the easiest place to hide a change in the rules. |
| ci | high, human | Workflows run with the pipeline's secrets. |
| auth | high | Sessions, tokens, permissions, secrets, crypto, CORS, row-level security. |
| payments | high | Money moves. |
| data-migration | high | Stored data changes shape, often irreversibly. |
| infra | high | Deployment and runtime configuration, `.env` files. |
| dependencies | medium | New third-party code runs with your permissions. |
| public-api | medium | Other code and people depend on the contract. |

## Keep the floor small

A path list is a weak router on its own. In Meta's published replay, expert-chosen sensitive paths caught 38% of outage-causing changes at the same gating level where a learned risk model caught about 61%. A floor that covers half the repo trains people to ignore it. Use the floor for the few places where a mistake is expensive no matter how small the diff, and let judgement and `risk` lessons do the rest.

Two habits from teams that run this at scale are worth copying:

- **Log overrides.** When someone merges past the router's tier, record who and why. Cloudflare's reviewers can "break glass" around their blocking bot; it's used on well under 1% of changes and every use is logged. Here, the record is a lesson or a note in the PR.
- **Watch reverts by tier.** If changes the router called low start getting reverted, raise the floor for those paths (a `risk` lesson does it without editing the policy) until the rate settles.
