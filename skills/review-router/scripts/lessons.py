#!/usr/bin/env python3
"""Read, check and extend REVIEW-LESSONS.md, the review agent's memory for a repo.

The same script ships with review-router, review-apprentice and spec-review.
See references/lessons.md for the format and the rules.

Usage:
    python lessons.py show [--base REF] [--diff RANGE | --paths P ...] [--org-file PATH] [--json]
    python lessons.py draft --kind K --scope GLOBS --title T --why W --taught-by WHO
                            [--evidence E] [--expires YYYY-MM-DD]
    python lessons.py add --entry-file PATH
    python lessons.py lint [--file PATH]

`show` reads the lessons file from the base branch (the merge base of --base and
HEAD), never from the change being reviewed, so a change can't rewrite the rules
of its own review. Standard library only; needs git on PATH for everything but lint.
"""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

LESSONS_FILE = "REVIEW-LESSONS.md"
KINDS = ("convention", "gotcha", "risk", "decision", "glossary", "quiet")
STATUSES = ("active", "stale", "retired")
REQUIRED = ("scope", "kind", "why", "taught by", "status")
HEADING = re.compile(r"^##\s+(L-(\d+))\s+(.*\S)\s*$")
FIELD = re.compile(r"^-\s+([A-Za-z][A-Za-z ]*?)\s*:\s*(.*)$")
EVIDENCE = re.compile(r"^(?P<path>[^:@]+?)(?::(?P<start>\d+)(?:-(?P<end>\d+))?)?\s*(?:@\s*(?P<sha>[0-9a-fA-F]{4,40}))?$")
FILE_HEADER = (
    "# Review lessons\n\n"
    "What the people on this project have taught the review agents, in their own words.\n"
    "Format and rules: references/lessons.md in the review skills.\n"
)


def utf8_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def git(*args, check=True):
    """Run git and return stdout, or None when check is False and git fails."""
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


def repo_root():
    out = git("rev-parse", "--show-toplevel", check=False)
    return Path(out.strip()) if out else None


def default_base():
    """origin/HEAD if set, else the first of main, master, origin/main, origin/master."""
    ref = git("symbolic-ref", "--quiet", "refs/remotes/origin/HEAD", check=False)
    if ref and ref.strip():
        return ref.strip().replace("refs/remotes/", "", 1)
    for name in ("main", "master", "origin/main", "origin/master"):
        if git("rev-parse", "--verify", "--quiet", name, check=False):
            return name
    return None


def merge_base(base):
    mb = git("merge-base", base, "HEAD", check=False)
    return mb.strip() if mb and mb.strip() else base


def read_at(ref, path):
    return git("show", f"{ref}:{path}", check=False)


# --- parsing -----------------------------------------------------------------

def parse(text, source="repo"):
    """Return the lessons in a file as dicts: id, num, title, line, source, fields."""
    lessons, current, last_key = [], None, None
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        head = HEADING.match(line)
        if head:
            current = {"id": head.group(1), "num": int(head.group(2)), "title": head.group(3),
                       "line": lineno, "source": source, "fields": {}}
            lessons.append(current)
            last_key = None
            continue
        if current is None:
            continue
        if line.startswith("## ") or line.startswith("# "):
            current, last_key = None, None
            continue
        field = FIELD.match(line)
        if field:
            last_key = field.group(1).strip().lower()
            current["fields"][last_key] = field.group(2).strip()
        elif last_key and raw.startswith("  ") and line.strip():
            current["fields"][last_key] += " " + line.strip()
    return lessons


def scopes(lesson):
    return [s.strip().replace("\\", "/") for s in lesson["fields"].get("scope", "").split(",") if s.strip()]


def glob_regex(glob):
    """Translate a path glob: ** crosses folders, * and ? stay inside one."""
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
    pattern = "".join(out)
    if not glob.endswith("*") and "." not in glob.rsplit("/", 1)[-1]:
        pattern += "(?:/.*)?"  # a bare folder name covers everything under it
    return re.compile("^" + pattern + "$")


def applies_to(lesson, paths):
    globs = scopes(lesson)
    if not globs or not paths:
        return True
    regexes = [glob_regex(g) for g in globs]
    return any(r.match(p) for r in regexes for p in paths)


def specificity(lesson):
    """Longer literal prefixes mean narrower scope; used to order output."""
    globs = scopes(lesson) or ["**"]
    return max(len(g.split("*", 1)[0]) for g in globs)


# --- checks ------------------------------------------------------------------

def check_evidence(evidence, base_commit):
    """Compare each cited block with the base. Returns a list of (item, state, note)."""
    results = []
    for item in [e.strip() for e in evidence.split(";") if e.strip()]:
        m = EVIDENCE.match(item)
        if not m:
            results.append((item, "unchecked", "not in path:start-end @ commit form"))
            continue
        path, sha = m.group("path").strip(), m.group("sha")
        start = int(m.group("start")) if m.group("start") else None
        end = int(m.group("end")) if m.group("end") else start
        now = read_at(base_commit, path) if base_commit else None
        if base_commit and now is None:
            results.append((item, "stale", "the file no longer exists at the base"))
            continue
        if not sha or not base_commit:
            results.append((item, "unchecked", "no commit to compare with"))
            continue
        then = read_at(sha, path)
        if then is None:
            results.append((item, "unchecked", f"commit {sha} or path not found locally"))
            continue
        if start is None:
            state = "ok" if then == now else "stale"
            results.append((item, state, "" if state == "ok" else "the file changed since the lesson was written"))
            continue
        old_block = then.splitlines()[start - 1:end]
        new_lines = now.splitlines()
        if not old_block:
            results.append((item, "unchecked", "cited lines are outside the file at that commit"))
        elif new_lines[start - 1:end] == old_block:
            results.append((item, "ok", ""))
        elif any(new_lines[i:i + len(old_block)] == old_block for i in range(len(new_lines))):
            results.append((item, "moved", "the cited lines moved but are unchanged"))
        else:
            results.append((item, "stale", "the cited lines changed since the lesson was written"))
    return results


def touched_by_change(evidence, base_commit, head):
    """Evidence items whose cited lines this change edits: the lesson is about code under review."""
    touched = []
    for item in [e.strip() for e in evidence.split(";") if e.strip()]:
        m = EVIDENCE.match(item)
        if not m:
            continue
        path = m.group("path").strip()
        before, after = read_at(base_commit, path), read_at(head, path)
        if before is None or before == after:
            continue
        if after is None:
            touched.append(item)
            continue
        if not m.group("start"):
            touched.append(item)
            continue
        start = int(m.group("start"))
        end = int(m.group("end")) if m.group("end") else start
        block = before.splitlines()[start - 1:end]
        after_lines = after.splitlines()
        if block and not any(after_lines[i:i + len(block)] == block for i in range(len(after_lines))):
            touched.append(item)
    return touched


def expired(lesson, today):
    raw = lesson["fields"].get("expires", "")
    try:
        return bool(raw) and dt.date.fromisoformat(raw[:10]) < today
    except ValueError:
        return False


def lint_lessons(lessons):
    problems, seen = [], {}
    for les in lessons:
        where = f"{les['id']} (line {les['line']})"
        f = les["fields"]
        for key in REQUIRED:
            if not f.get(key):
                problems.append(f"{where}: missing '{key}'")
        kind = f.get("kind", "").lower()
        if kind and kind not in KINDS:
            problems.append(f"{where}: kind '{kind}' is not one of {', '.join(KINDS)}")
        status = f.get("status", "").lower()
        if status and status not in STATUSES:
            problems.append(f"{where}: status '{status}' is not one of {', '.join(STATUSES)}")
        if kind == "quiet" and not f.get("expires"):
            problems.append(f"{where}: a quiet lesson needs 'expires' (YYYY-MM-DD)")
        if f.get("expires"):
            try:
                dt.date.fromisoformat(f["expires"][:10])
            except ValueError:
                problems.append(f"{where}: expires '{f['expires']}' is not YYYY-MM-DD")
        for item in [e.strip() for e in f.get("evidence", "").split(";") if e.strip()]:
            if not EVIDENCE.match(item):
                problems.append(f"{where}: evidence '{item}' is not path:start-end @ commit")
        if les["num"] in seen:
            problems.append(f"{where}: number already used by {seen[les['num']]}")
        seen.setdefault(les["num"], where)
    return problems


# --- commands ----------------------------------------------------------------

def changed_paths(diff_range):
    out = git("diff", "--name-only", diff_range)
    return [p.strip() for p in out.splitlines() if p.strip()]


def cmd_show(args):
    if not repo_root():
        sys.exit("Not inside a git repository. Run this from the repo being reviewed.")
    base = args.base or default_base()
    if not base:
        sys.exit("Couldn't find a base branch. Pass --base (for example --base origin/main).")
    base_commit = merge_base(base)
    base_text = read_at(base_commit, LESSONS_FILE)
    head_text = read_at("HEAD", LESSONS_FILE)
    root = repo_root()
    work_text = (root / LESSONS_FILE).read_text(encoding="utf-8") if (root / LESSONS_FILE).is_file() else None
    edited_here = (head_text or "") != (base_text or "") or (work_text or "") != (head_text or "")

    lessons = parse(base_text or "", source="repo")
    if args.org_file:
        org_path = Path(args.org_file)
        if not org_path.is_file():
            sys.exit(f"--org-file {org_path} not found.")
        lessons += parse(org_path.read_text(encoding="utf-8"), source="org")

    if args.diff:
        paths = changed_paths(args.diff)
        head = re.split(r"\.\.\.?", args.diff)[-1] or "HEAD"
    else:
        paths = [p.replace("\\", "/") for p in (args.paths or [])]
        head = "HEAD"

    today = dt.date.today()
    report = {"base": base, "base_commit": base_commit, "lessons_file_at_base": base_text is not None,
              "lessons_file_edited_in_this_change": edited_here, "paths": paths,
              "apply": [], "ask": [], "not_applied": []}
    for les in sorted(lessons, key=lambda x: (x["source"] != "repo", -specificity(x), x["num"])):
        if not applies_to(les, paths):
            continue
        f = les["fields"]
        entry = {"id": les["id"], "title": les["title"], "source": les["source"],
                 "kind": f.get("kind", ""), "scope": f.get("scope", ""), "why": f.get("why", ""),
                 "taught_by": f.get("taught by", ""), "evidence": []}
        status = f.get("status", "active").lower()
        if status == "retired":
            entry["reason"] = "retired"
            report["not_applied"].append(entry)
            continue
        if expired(les, today):
            entry["reason"] = f"expired {f.get('expires')}"
            report["not_applied"].append(entry)
            continue
        checks = check_evidence(f.get("evidence", ""), base_commit) if f.get("evidence") else []
        entry["evidence"] = [{"item": i, "state": s, "note": n} for i, s, n in checks]
        entry["touched_by_change"] = touched_by_change(f.get("evidence", ""), base_commit, head)
        if status == "stale" or any(s == "stale" for _, s, _ in checks):
            entry["reason"] = "marked stale" if status == "stale" else "evidence changed"
            report["ask"].append(entry)
        else:
            report["apply"].append(entry)

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"Lessons from {LESSONS_FILE} at the base ({base} -> {base_commit[:10]})")
    if paths:
        print(f"Filtered to {len(paths)} changed path(s).")
    if base_text is None:
        print(f"\nNo {LESSONS_FILE} at the base yet. Nothing to apply; lessons can still be proposed.")
    if edited_here:
        print(f"\nNOTE: this change edits {LESSONS_FILE}. Those edits do not apply to this review;"
              " they take effect after a human merges them. Mention this in the review.")

    def show(title, items, with_reason=False):
        print(f"\n## {title} ({len(items)})")
        if not items:
            print("(none)")
        for e in items:
            tag = " [org]" if e["source"] == "org" else ""
            reason = f" ({e['reason']})" if with_reason and e.get("reason") else ""
            print(f"\n- {e['id']}{tag} {e['title']}{reason}")
            print(f"  kind: {e['kind']} | scope: {e['scope']}")
            print(f"  why: {e['why']}")
            print(f"  taught by: {e['taught_by']}")
            for ev in e["evidence"]:
                note = f" - {ev['note']}" if ev["note"] else ""
                print(f"  evidence: {ev['item']} [{ev['state']}{note}]")
            for item in e.get("touched_by_change", []):
                print(f"  THIS CHANGE EDITS the code this lesson cites ({item}): check it against the lesson,"
                      " and ask whether the lesson still holds afterwards.")

    show("Apply", report["apply"])
    show("Ask a human before applying", report["ask"], with_reason=True)
    show("Not applied", report["not_applied"], with_reason=True)
    return 0


def local_file(path=None):
    if path:
        return Path(path)
    root = repo_root()
    return (root or Path.cwd()) / LESSONS_FILE


def next_number(*texts):
    nums = [les["num"] for t in texts if t for les in parse(t)]
    return max(nums, default=0) + 1


def cmd_draft(args):
    kind = args.kind.lower()
    if kind not in KINDS:
        sys.exit(f"--kind must be one of {', '.join(KINDS)}")
    if kind == "quiet" and not args.expires:
        sys.exit("A quiet lesson needs --expires YYYY-MM-DD (90 days is a sensible default).")
    path = local_file()
    work = path.read_text(encoding="utf-8") if path.is_file() else None
    base = default_base() if repo_root() else None
    base_text = read_at(merge_base(base), LESSONS_FILE) if base else None
    num = next_number(work, base_text)
    lines = [f"## L-{num:03d} {args.title.strip()}",
             f"- scope: {args.scope.strip()}",
             f"- kind: {kind}",
             f"- why: {args.why.strip()}"]
    if args.evidence:
        lines.append(f"- evidence: {args.evidence.strip()}")
    lines.append(f"- taught by: {args.taught_by.strip()}")
    if args.expires:
        lines.append(f"- expires: {args.expires.strip()}")
    lines.append("- status: active")
    print("\n".join(lines))
    print("\n(Draft only, nothing written. Let the human edit the why, then save it to a file"
          " and run: python lessons.py add --entry-file <file>)", file=sys.stderr)
    return 0


def cmd_add(args):
    entry_text = Path(args.entry_file).read_text(encoding="utf-8").strip()
    new = parse(entry_text)
    if len(new) != 1:
        sys.exit("The entry file must hold exactly one '## L-<number> <title>' lesson.")
    problems = lint_lessons(new)
    if problems:
        sys.exit("The entry has problems:\n  " + "\n  ".join(problems))
    path = local_file()
    existing = path.read_text(encoding="utf-8") if path.is_file() else FILE_HEADER
    if any(les["num"] == new[0]["num"] for les in parse(existing)):
        sys.exit(f"{new[0]['id']} is already used in {path}. Re-run draft for the next free number.")
    text = existing.rstrip() + "\n\n" + entry_text + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Added {new[0]['id']} to {path}. Commit it so it reaches the base branch through review.")
    return 0


def cmd_lint(args):
    path = local_file(args.file)
    if not path.is_file():
        print(f"{path} not found: nothing to check.")
        return 0
    lessons = parse(path.read_text(encoding="utf-8"))
    problems = lint_lessons(lessons)
    for p in problems:
        print(p)
    print(f"{len(lessons)} lesson(s), {len(problems)} problem(s) in {path}")
    return 1 if problems else 0


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show", help="lessons that apply to a change, read from the base branch")
    s.add_argument("--base", help="base branch or commit (default: origin/HEAD, main or master)")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--diff", help="git diff range for the change, e.g. origin/main...HEAD")
    g.add_argument("--paths", nargs="+", help="paths to filter lessons by")
    s.add_argument("--org-file", help="an organisation-wide lessons file to include")
    s.add_argument("--json", action="store_true", help="machine-readable output")

    d = sub.add_parser("draft", help="print a new entry for a human to edit (writes nothing)")
    d.add_argument("--kind", required=True)
    d.add_argument("--scope", required=True)
    d.add_argument("--title", required=True)
    d.add_argument("--why", required=True)
    d.add_argument("--taught-by", required=True)
    d.add_argument("--evidence")
    d.add_argument("--expires")

    a = sub.add_parser("add", help="append a human-accepted entry to the working tree file")
    a.add_argument("--entry-file", required=True)

    li = sub.add_parser("lint", help="check the lessons file")
    li.add_argument("--file", help=f"path to the file (default: {LESSONS_FILE} at the repo root)")

    args = ap.parse_args()
    return {"show": cmd_show, "draft": cmd_draft, "add": cmd_add, "lint": cmd_lint}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
