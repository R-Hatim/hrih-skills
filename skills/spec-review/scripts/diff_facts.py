#!/usr/bin/env python3
"""Deterministic facts about a change, for a reviewer to reason from.

Lists what changed, which files fall into sensitive categories (and the minimum
review tier each one sets), size, dependency changes, and test changes that
deserve a second look (removed assertions, new skip/only markers, deleted
tests, tests edited in the same change as the code they test).

Usage:
    python diff_facts.py [--base REF] [--head REF] [--worktree] [--json]
    python diff_facts.py --range A..B [--json]

The base defaults to origin/HEAD, main or master; the change is compared from
its merge base with HEAD, like a pull request. --worktree includes uncommitted
edits. A repo can tune the categories in .review/policy.json, which is read
from the base, never from the change (see references/router-policy.md).
Standard library only; needs git on PATH.
"""
import argparse
import json
import re
import subprocess
import sys

TIERS = ("low", "medium", "high")

# Each category: a minimum tier and patterns tested against the path.
# "words" match whole words in any path segment (camelCase and snake_case are
# split first, so "tokenizer.py" doesn't count as a token file but
# "accessToken.ts" does). "globs" match the whole path.
DEFAULT_POLICY = {
    "large_change_lines": 400,
    "huge_change_lines": 1000,
    "categories": {
        "review-config": {"tier": "high", "human": True,
                          "why": "edits the rules the reviewers and agents follow",
                          "globs": ["REVIEW-LESSONS.md", ".review/**", "**/CODEOWNERS", "REVIEW.md",
                                    "**/REVIEW.md", "AGENTS.md", "**/AGENTS.md", "CLAUDE.md",
                                    "**/CLAUDE.md", ".claude/**", ".cursor/**", ".github/copilot-instructions.md"]},
        "ci": {"tier": "high", "human": True, "why": "changes what runs with the pipeline's secrets",
               "globs": [".github/workflows/**", ".gitea/workflows/**", ".forgejo/workflows/**",
                         ".gitlab-ci.yml", ".circleci/**", "Jenkinsfile", "azure-pipelines.yml",
                         ".buildkite/**", "bitbucket-pipelines.yml"]},
        "auth": {"tier": "high", "why": "authentication, sessions, permissions or secrets",
                 "words": ["auth", "authn", "authz", "authentication", "authorization", "authorize",
                           "login", "logout", "signin", "session", "sessions", "token", "tokens", "jwt",
                           "oauth", "oidc", "saml", "sso", "permission", "permissions", "rbac", "acl",
                           "password", "passwords", "credential", "credentials", "crypto", "secret",
                           "secrets", "csrf", "cors", "rls"]},
        "payments": {"tier": "high", "why": "money moves here",
                     "words": ["payment", "payments", "billing", "invoice", "invoices", "stripe",
                               "checkout", "refund", "refunds", "charge", "charges", "subscription",
                               "subscriptions", "ledger", "payout", "payouts"]},
        "data-migration": {"tier": "high", "why": "changes stored data or its shape",
                           "words": ["migration", "migrations", "migrate", "schema"],
                           "globs": ["**/*.sql"]},
        "infra": {"tier": "high", "why": "deployment and runtime configuration",
                  "globs": ["**/*.tf", "**/Dockerfile", "**/Dockerfile.*", "**/docker-compose*.yml",
                            "**/compose*.yml", "**/compose*.yaml", "deploy/**", "infra/**", "k8s/**",
                            "helm/**", "**/Caddyfile", "**/nginx*.conf", "**/*.service", "**/.env*"]},
        "dependencies": {"tier": "medium", "why": "adds or changes third-party code",
                         "globs": ["**/package.json", "**/package-lock.json", "**/pnpm-lock.yaml",
                                   "**/yarn.lock", "**/requirements*.txt", "**/pyproject.toml",
                                   "**/poetry.lock", "**/uv.lock", "**/Pipfile*", "**/Cargo.toml",
                                   "**/Cargo.lock", "**/go.mod", "**/go.sum", "**/*.csproj",
                                   "**/Directory.Packages.props", "**/packages.lock.json", "**/pom.xml",
                                   "**/build.gradle*", "**/Gemfile*", "**/composer.json", "**/composer.lock"]},
        "public-api": {"tier": "medium", "why": "a contract other code or people depend on",
                       "globs": ["**/openapi*.*", "**/swagger*.*", "**/*.proto", "**/*.graphql",
                                 "**/*.gql"]},
    },
}

LOCKFILES = re.compile(r"(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|poetry\.lock|uv\.lock|"
                       r"Cargo\.lock|go\.sum|packages\.lock\.json|composer\.lock|Gemfile\.lock)$")
GENERATED = re.compile(r"(^|/)(dist|build|vendor|node_modules|\.next|target|obj)/|\.min\.(js|css)$")
TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs", "testing", "e2e", "fixtures"}
TEST_FILE = re.compile(
    r"(^test_.*\.py$|_test\.py$|_test\.go$|\.test\.[cm]?[jt]sx?$|\.spec\.[cm]?[jt]sx?$|Tests?\.(java|kt|cs)$|"
    r"_spec\.rb$|_test\.rb$|Tests?\.swift$|_test\.dart$|\.test\.mjs$)", re.IGNORECASE)
ASSERTION = re.compile(r"\b(assert\w*|expect|should|Assert\.|XCTAssert\w*|require\.\w+|t\.(Error|Fatal)\w*|"
                       r"check\(|verify\(|toBe|toEqual|toMatch|toThrow|assert_eq!|assert!|panic!)", re.IGNORECASE)
SKIP_MARK = re.compile(r"(@pytest\.mark\.(skip|xfail)|pytest\.skip\(|@unittest\.skip|\bxit\(|\bxdescribe\(|"
                       r"\b(it|test|describe)\.(skip|only|todo)\(|\bfit\(|\bfdescribe\(|@Ignore\b|@Disabled\b|"
                       r"\[Fact\(Skip|\[Theory\(Skip|\[Ignore|#\[ignore\]|t\.Skip\(|\.skip\(\)|\bpending\()")
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


def utf8_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def git(*args, check=True):
    try:
        proc = subprocess.run(["git", *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    except FileNotFoundError:
        sys.exit("git was not found on PATH.")
    if proc.returncode != 0:
        if check:
            sys.exit(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
        return None
    return proc.stdout


def default_base():
    ref = git("symbolic-ref", "--quiet", "refs/remotes/origin/HEAD", check=False)
    if ref and ref.strip():
        return ref.strip().replace("refs/remotes/", "", 1)
    for name in ("main", "master", "origin/main", "origin/master"):
        if git("rev-parse", "--verify", "--quiet", name, check=False):
            return name
    return None


def glob_regex(glob):
    glob = glob.strip()
    if glob.startswith("./"):  # only a leading "./"; dotted names like .github/ must survive
        glob = glob[2:]
    out, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$", re.IGNORECASE)


def path_words(path):
    words = set()
    for seg in path.split("/"):
        seg = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", seg)
        words.update(w for w in re.split(r"[^a-z0-9]+", seg.lower()) if w)
    return words


def is_test(path):
    parts = path.lower().split("/")
    return bool(TEST_DIRS.intersection(parts[:-1])) or bool(TEST_FILE.search(parts[-1]))


def load_policy(base_commit):
    """Default policy, overlaid with .review/policy.json from the base if present."""
    policy = json.loads(json.dumps(DEFAULT_POLICY))
    raw = git("show", f"{base_commit}:.review/policy.json", check=False)
    source = "defaults"
    if raw:
        try:
            custom = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"warning: .review/policy.json at the base is not valid JSON ({e}); using defaults",
                  file=sys.stderr)
            return policy, "defaults (policy.json invalid)"
        for key in ("large_change_lines", "huge_change_lines"):
            if key in custom:
                policy[key] = int(custom[key])
        for name, cat in custom.get("categories", {}).items():
            if cat is None:
                policy["categories"].pop(name, None)
            else:
                policy["categories"][name] = {**policy["categories"].get(name, {}), **cat}
        source = ".review/policy.json at the base, over the defaults"
    return policy, source


def categorise(path, policy):
    hits = []
    words = path_words(path)
    for name, cat in policy["categories"].items():
        by_glob = any(glob_regex(g).match(path) for g in cat.get("globs", []))
        by_word = bool(words.intersection(w.lower() for w in cat.get("words", [])))
        if by_glob or by_word:
            hits.append(name)
    return hits


def parse_diff(diff_text):
    """Per-file hunks and the added/removed lines inside them."""
    files, current = {}, None
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            current = None
        elif line.startswith("+++ "):
            path = line[4:].strip()
            if path == "/dev/null":
                continue
            current = files.setdefault(path[2:] if path.startswith("b/") else path,
                                       {"hunks": [], "added": [], "removed": []})
        elif line.startswith("--- "):
            path = line[4:].strip()
            if path != "/dev/null":
                old = path[2:] if path.startswith("a/") else path
                current = files.setdefault(old, {"hunks": [], "added": [], "removed": []})
        elif current is not None and line.startswith("@@"):
            m = HUNK.match(line)
            if m:
                current["hunks"].append({"old_start": int(m.group(1)), "old_len": int(m.group(2) or 1),
                                         "new_start": int(m.group(3)), "new_len": int(m.group(4) or 1),
                                         "context": m.group(5).strip()})
        elif current is not None and line.startswith("+") and not line.startswith("+++"):
            current["added"].append(line[1:])
        elif current is not None and line.startswith("-") and not line.startswith("---"):
            current["removed"].append(line[1:])
    return files


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", help="base branch or commit (default: origin/HEAD, main or master)")
    ap.add_argument("--head", default="HEAD", help="head of the change (default: HEAD)")
    ap.add_argument("--range", help="explicit git range, e.g. abc123..def456 (overrides --base/--head)")
    ap.add_argument("--worktree", action="store_true", help="compare the base with the working tree")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    if not git("rev-parse", "--show-toplevel", check=False):
        sys.exit("Not inside a git repository.")

    if args.range:
        left = args.range.split("...")[0].split("..")[0]
        base_commit = git("rev-parse", left).strip()
        spec = [args.range]
        label = args.range
    else:
        base = args.base or default_base()
        if not base:
            sys.exit("Couldn't find a base branch. Pass --base or --range.")
        mb = git("merge-base", base, args.head, check=False)
        base_commit = mb.strip() if mb and mb.strip() else git("rev-parse", base).strip()
        if not args.worktree and git("rev-parse", args.head).strip() == base_commit:
            # Reviewing from the base branch itself: the change must be another branch.
            others = [b for b in git("for-each-ref", "--format=%(refname:short)", "refs/heads").split()
                      if git("rev-parse", b).strip() != base_commit]
            if len(others) != 1:
                sys.exit(f"{args.head} is the base itself, so there's no change to look at. Pass --head <branch>"
                         + (f" (branches: {', '.join(others)})." if others else "."))
            args.head = others[0]
            print(f"note: {base} is checked out; reviewing branch {args.head} as the change"
                  " (pass --head to choose another).", file=sys.stderr)
            mb = git("merge-base", base, args.head, check=False)
            base_commit = mb.strip() if mb and mb.strip() else base_commit
        if args.worktree:
            spec, label = [base_commit], f"{base} (merge base {base_commit[:10]}) .. working tree"
        else:
            spec, label = [f"{base_commit}..{args.head}"], f"{base} (merge base {base_commit[:10]}) .. {args.head}"

    policy, policy_source = load_policy(base_commit)
    numstat = git("diff", "--numstat", "-M", *spec)
    status_out = git("diff", "--name-status", "-M", *spec)
    diff_text = git("diff", "-U0", "-M", *spec)
    hunks = parse_diff(diff_text)

    statuses = {}
    for line in status_out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            statuses[parts[-1]] = parts[0][0]

    files = []
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added, removed, path = parts[0], parts[1], parts[-1]
        if " => " in path:  # rename shown as {a => b}
            path = re.sub(r"\{[^}]* => ([^}]*)\}", r"\1", path).replace("//", "/")
        binary = added == "-"
        entry = {"path": path, "status": statuses.get(path, "M"), "added": 0 if binary else int(added),
                 "removed": 0 if binary else int(removed), "binary": binary, "test": is_test(path),
                 "generated": bool(LOCKFILES.search(path) or GENERATED.search(path)),
                 "categories": categorise(path, policy), "hunks": hunks.get(path, {}).get("hunks", [])}
        files.append(entry)

    reviewed = [f for f in files if not f["generated"]]
    total_added = sum(f["added"] for f in reviewed)
    total_removed = sum(f["removed"] for f in reviewed)
    changed_lines = total_added + total_removed

    floor, reasons, human_required = "low", [], []
    for f in files:
        for name in f["categories"]:
            cat = policy["categories"][name]
            tier = cat.get("tier", "medium")
            if TIERS.index(tier) > TIERS.index(floor):
                floor = tier
            reasons.append({"path": f["path"], "category": name, "tier": tier, "why": cat.get("why", "")})
            if cat.get("human"):
                human_required.append(f["path"])
    if changed_lines > policy["large_change_lines"] and TIERS.index(floor) < 1:
        floor = "medium"
        reasons.append({"path": "*", "category": "size", "tier": "medium",
                        "why": f"{changed_lines} changed lines; large changes get shallower reviews"})

    source_files = [f for f in files if not f["test"] and not f["generated"]]
    test_files = [f for f in files if f["test"]]
    removed_asserts, new_skips = [], []
    for f in test_files:
        h = hunks.get(f["path"], {})
        removed_asserts += [{"path": f["path"], "line": ln.strip()} for ln in h.get("removed", [])
                            if ASSERTION.search(ln)]
        new_skips += [{"path": f["path"], "line": ln.strip()} for ln in h.get("added", []) if SKIP_MARK.search(ln)]
    dep_changes = []
    for f in files:
        if "dependencies" in f["categories"] and not LOCKFILES.search(f["path"]):
            added_lines = [ln.strip() for ln in hunks.get(f["path"], {}).get("added", []) if ln.strip()]
            dep_changes.append({"path": f["path"], "added_lines": added_lines[:20]})

    facts = {
        "range": label,
        "base_commit": base_commit,
        "policy": policy_source,
        "totals": {"files": len(files), "source_files": len(source_files), "test_files": len(test_files),
                   "added": total_added, "removed": total_removed, "generated_files": len(files) - len(reviewed)},
        "floor_tier": floor,
        "floor_reasons": reasons,
        "human_required": sorted(set(human_required)),
        "too_big_to_review_well": changed_lines > policy["huge_change_lines"],
        "tests": {
            "changed_with_code": bool(test_files) and bool(source_files),
            "code_without_test_changes": bool(source_files) and not test_files,
            "deleted": [f["path"] for f in test_files if f["status"] == "D"],
            "removed_assertions": removed_asserts[:30],
            "new_skip_or_only_markers": new_skips[:30],
        },
        "dependencies": dep_changes,
        "files": files,
    }

    if args.json:
        print(json.dumps(facts, indent=2))
        return 0

    t = facts["totals"]
    print(f"Change: {label}")
    print(f"Policy: {policy_source}")
    print(f"{t['files']} files ({t['source_files']} source, {t['test_files']} test, {t['generated_files']} generated"
          f" or lockfiles), +{t['added']} -{t['removed']} lines excluding generated")
    print(f"\nFloor tier: {floor.upper()}  (the review tier can go up from here, never down)")
    for r in reasons:
        print(f"  - {r['path']}: {r['category']} -> {r['tier']} ({r['why']})")
    if facts["human_required"]:
        print("\nA human must approve (policy): " + ", ".join(facts["human_required"]))
    if facts["too_big_to_review_well"]:
        print(f"\nThis change is over {policy['huge_change_lines']} lines. Suggest splitting it.")
    tests = facts["tests"]
    print("\nTests:")
    if tests["code_without_test_changes"]:
        print("  - source changed and no test changed")
    if tests["changed_with_code"]:
        print("  - tests changed in the same change as the code: check they weren't bent to fit it")
    for p in tests["deleted"]:
        print(f"  - deleted test file: {p}")
    for a in tests["removed_assertions"]:
        print(f"  - removed assertion in {a['path']}: {a['line'][:120]}")
    for s in tests["new_skip_or_only_markers"]:
        print(f"  - new skip/only marker in {s['path']}: {s['line'][:120]}")
    if not any([tests["code_without_test_changes"], tests["changed_with_code"], tests["deleted"],
                tests["removed_assertions"], tests["new_skip_or_only_markers"]]):
        print("  - nothing notable")
    if dep_changes:
        print("\nDependency manifests changed:")
        for d in dep_changes:
            print(f"  - {d['path']}")
            for ln in d["added_lines"][:8]:
                print(f"      + {ln[:120]}")
    print("\nFiles:")
    for f in files:
        flags = ", ".join(x for x in ([f["status"]] + (["test"] if f["test"] else []) +
                                      (["generated"] if f["generated"] else []) + f["categories"]) if x)
        size = "binary" if f["binary"] else f"+{f['added']} -{f['removed']}"
        print(f"  {f['path']}  [{flags}]  {size}, {len(f['hunks'])} hunk(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
