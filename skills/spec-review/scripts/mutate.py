#!/usr/bin/env python3
"""A small, language-agnostic mutation pass over the lines a change touched.

It plants one small bug at a time in the changed source lines (flip a
comparison, shift a boundary, swap and/or, negate a condition, flip a boolean,
nudge a +1), runs the test command, and records whether the tests noticed.
A mutant the tests don't notice ("survived") is a behaviour the tests don't
pin down. That is a question for the human reviewer, not proof of a bug.

Usage:
    python mutate.py --test "pytest -q" [--base REF | --range A..B] [--files F ...]
                     [--max 25] [--timeout SECONDS] [--setup "npm ci"] [--in-place]
                     [--out report.json] [--json]

By default it works in a temporary git worktree at HEAD, so your checkout is
never touched; pass --setup to install dependencies there (node_modules and
build outputs aren't copied). --in-place mutates your working tree instead and
restores every file afterwards. Standard library only; needs git on PATH.
"""
import argparse
import json
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs", "testing", "e2e", "fixtures"}
TEST_FILE = re.compile(
    r"(^test_.*\.py$|_test\.py$|_test\.go$|\.test\.[cm]?[jt]sx?$|\.spec\.[cm]?[jt]sx?$|Tests?\.(java|kt|cs)$|"
    r"_spec\.rb$|_test\.rb$|Tests?\.swift$|_test\.dart$|\.test\.mjs$)", re.IGNORECASE)
SOURCE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".kt", ".cs",
              ".c", ".h", ".cc", ".cpp", ".hpp", ".rb", ".php", ".swift", ".dart", ".scala", ".lua"}
WORD_LOGIC_EXT = {".py", ".rb", ".lua"}
COMMENT = re.compile(r"^\s*(#|//|/\*|\*|--|;|<!--)")
SKIP_LINE = re.compile(r"^\s*(import |from \S+ import|using |#include|package |use |require\(|@)")
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

# (name, pattern, replacement, extensions or None for all)
OPERATORS = [
    ("eq-to-neq", r"(?<![=!<>])===(?!=)", "!==", None),
    ("neq-to-eq", r"!==(?!=)", "===", None),
    ("eq-to-neq", r"(?<![=!<>])==(?!=)", "!=", None),
    ("neq-to-eq", r"!=(?!=)", "==", None),
    ("le-to-lt", r"(?<![<>=])<=(?!=)", "<", None),
    ("ge-to-gt", r"(?<![<>=])>=(?!=)", ">", None),
    ("lt-to-le", r"(?<=\s)<(?=\s)", "<=", None),
    ("gt-to-ge", r"(?<=\s)>(?=\s)", ">=", None),
    ("and-to-or", r"&&", "||", None),
    ("or-to-and", r"\|\|", "&&", None),
    ("and-to-or", r"(?<=\s)and(?=\s)", "or", WORD_LOGIC_EXT),
    ("or-to-and", r"(?<=\s)or(?=\s)", "and", WORD_LOGIC_EXT),
    ("drop-not", r"(?<=\bif\s)not\s+", "", WORD_LOGIC_EXT),
    ("drop-negation", r"!(?=[A-Za-z_(])", "", None),
    ("true-to-false", r"\btrue\b", "false", None),
    ("false-to-true", r"\bfalse\b", "true", None),
    ("true-to-false", r"\bTrue\b", "False", None),
    ("false-to-true", r"\bFalse\b", "True", None),
    ("plus-one-to-minus", r"(?<=\s)\+\s*1\b", "- 1", None),
    ("minus-one-to-plus", r"(?<=\s)-\s*1\b", "+ 1", None),
    ("inc-to-dec", r"\+=\s*1\b", "-= 1", None),
]


def utf8_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def git(*args, cwd=None, check=True):
    proc = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=cwd)
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


def is_test(path):
    parts = path.lower().split("/")
    return bool(TEST_DIRS.intersection(parts[:-1])) or bool(TEST_FILE.search(parts[-1]))


def changed_lines(diff_range, only_files):
    """{path: set(new line numbers)} for added/changed lines in non-test source files."""
    diff = git("diff", "-U0", "--no-color", diff_range)
    result, path = {}, None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            p = line[4:].strip()
            path = None if p == "/dev/null" else (p[2:] if p.startswith("b/") else p)
        elif path and line.startswith("@@"):
            m = HUNK.match(line)
            if m:
                start, length = int(m.group(1)), int(m.group(2) or 1)
                result.setdefault(path, set()).update(range(start, start + length))
    keep = {}
    for p, lines in result.items():
        if only_files and p not in only_files:
            continue
        if is_test(p) or Path(p).suffix.lower() not in SOURCE_EXT:
            continue
        if lines:
            keep[p] = lines
    return keep


def in_string(line, pos):
    """True if pos falls inside a simple quoted string (good enough for one line)."""
    quote = None
    i = 0
    while i < pos:
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'`":
            quote = ch
        i += 1
    return quote is not None


def block_lines(src, ext):
    """Line numbers inside multi-line docstrings or block comments, which aren't worth mutating."""
    inside, quiet = None, set()
    for n, raw in enumerate(src, 1):
        line = raw.rstrip("\r\n")
        if inside:
            quiet.add(n)
            if inside in line:
                inside = None
            continue
        if ext in (".py",):
            for q in ('"""', "'''"):
                if line.count(q) % 2 == 1:
                    inside = q
                    quiet.add(n)
                    break
        elif "/*" in line and "*/" not in line.split("/*", 1)[1]:
            inside = "*/"
            quiet.add(n)
    return quiet


def mutants_for(path, text, lines):
    ext = Path(path).suffix.lower()
    src = text.splitlines(keepends=True)
    skip = block_lines(src, ext)
    out = []
    for n in sorted(lines):
        if n < 1 or n > len(src) or n in skip:
            continue
        line = src[n - 1]
        body = line.rstrip("\r\n")
        if not body.strip() or COMMENT.match(body) or SKIP_LINE.match(body):
            continue
        seen = set()
        for name, pattern, repl, exts in OPERATORS:
            if exts and ext not in exts:
                continue
            for m in re.finditer(pattern, body):
                if in_string(body, m.start()):
                    continue
                mutated = body[:m.start()] + repl + body[m.end():]
                if mutated == body or mutated in seen:
                    continue
                seen.add(mutated)
                out.append({"path": path, "line": n, "operator": name, "original": body.strip(),
                            "mutated": mutated.strip(), "_new_line": mutated + line[len(body):]})
    return out


def pick(mutants, limit, seed):
    """Spread the budget across lines: one mutant per line first, then seconds, and so on."""
    rng = random.Random(seed)
    by_line = {}
    for m in mutants:
        by_line.setdefault((m["path"], m["line"]), []).append(m)
    for group in by_line.values():
        rng.shuffle(group)
    keys = list(by_line)
    rng.shuffle(keys)
    chosen, round_ = [], 0
    while len(chosen) < limit and any(len(by_line[k]) > round_ for k in keys):
        for k in keys:
            if len(by_line[k]) > round_ and len(chosen) < limit:
                chosen.append(by_line[k][round_])
        round_ += 1
    return sorted(chosen, key=lambda m: (m["path"], m["line"]))


def run(cmd, cwd, timeout):
    """Run a shell command; return (status, seconds, tail of output)."""
    start = time.time()
    kwargs = {"shell": True, "cwd": cwd, "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kwargs)
    try:
        out, _ = proc.communicate(timeout=timeout)
        status = "pass" if proc.returncode == 0 else "fail"
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        else:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        out, _ = proc.communicate()
        status = "timeout"
    text = (out or b"").decode("utf-8", errors="replace")
    return status, time.time() - start, "\n".join(text.strip().splitlines()[-15:])


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", required=True, help="command that runs the tests; exit 0 means pass")
    ap.add_argument("--base", help="base branch (default: origin/HEAD, main or master)")
    ap.add_argument("--range", help="explicit git range, e.g. abc..def (default: merge-base..HEAD)")
    ap.add_argument("--files", nargs="+", help="only mutate these changed files")
    ap.add_argument("--max", type=int, default=25, help="most mutants to run (default 25)")
    ap.add_argument("--timeout", type=float, help="seconds per test run (default: 3x the clean run + 30)")
    ap.add_argument("--setup", help="command to run once in the temporary worktree (e.g. 'npm ci')")
    ap.add_argument("--in-place", action="store_true", help="mutate the working tree instead of a worktree")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", help="also write the JSON report to this file")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args()

    root_out = git("rev-parse", "--show-toplevel", check=False)
    if not root_out:
        sys.exit("Not inside a git repository.")
    root = Path(root_out.strip())
    if args.range:
        diff_range = args.range
        head = re.split(r"\.\.\.?", args.range)[-1] or "HEAD"
    else:
        base = args.base or default_base()
        if not base:
            sys.exit("Couldn't find a base branch. Pass --base or --range.")
        mb = git("merge-base", base, "HEAD", check=False)
        diff_range, head = f"{(mb or base).strip()}..HEAD", "HEAD"
    head_sha = git("rev-parse", head).strip()
    only = {f.replace("\\", "/") for f in args.files} if args.files else None
    targets = changed_lines(diff_range, only)
    if not targets:
        print("No changed non-test source lines to mutate in " + diff_range)
        return 0

    workdir, cleanup = root, None
    if args.in_place:
        if head_sha != git("rev-parse", "HEAD").strip():
            sys.exit(f"--in-place needs the checkout at the change's head ({head}); drop --in-place to use"
                     " a temporary worktree at that commit instead.")
    else:
        if head_sha == git("rev-parse", "HEAD").strip():
            dirty = git("status", "--porcelain", "--", *targets.keys(), cwd=root)
            if dirty and dirty.strip():
                print("note: some target files have uncommitted edits; the worktree uses the committed"
                      " version, so those edits aren't tested. Commit them or use --in-place.", file=sys.stderr)
        tmp = Path(tempfile.mkdtemp(prefix="mutate-"))
        workdir = tmp / "wt"
        git("worktree", "add", "--detach", str(workdir), head_sha, cwd=root)

        def cleanup():
            git("worktree", "remove", "--force", str(workdir), cwd=root, check=False)
            shutil.rmtree(tmp, ignore_errors=True)

    originals = {}
    try:
        all_mutants = []
        for path, lines in targets.items():
            file = workdir / path
            if not file.is_file():
                continue
            text = file.read_bytes().decode("utf-8", errors="surrogateescape")
            originals[path] = file.read_bytes()
            all_mutants += mutants_for(path, text, lines)
        if not all_mutants:
            print("The changed lines have nothing this tool knows how to mutate"
                  " (no comparisons, boolean logic or +1s). Review the tests by reading them.")
            return 0
        chosen = pick(all_mutants, args.max, args.seed)

        if args.setup:
            status, secs, tail = run(args.setup, workdir, None)
            if status != "pass":
                print(f"Setup failed after {secs:.0f}s:\n{tail}")
                return 2
        status, base_secs, tail = run(args.test, workdir, args.timeout)
        if status != "pass":
            hint = "" if args.in_place or args.setup else (" In a fresh worktree, dependencies and build outputs"
                                                           " are missing: try --setup or --in-place.")
            print(f"The tests don't pass before any mutation ({status}).{hint}\n{tail}")
            return 2
        timeout = args.timeout or (base_secs * 3 + 30)

        results = []
        for i, m in enumerate(chosen, 1):
            file = workdir / m["path"]
            src = originals[m["path"]].decode("utf-8", errors="surrogateescape").splitlines(keepends=True)
            src[m["line"] - 1] = m["_new_line"]
            file.write_bytes("".join(src).encode("utf-8", errors="surrogateescape"))
            try:
                status, secs, tail = run(args.test, workdir, timeout)
            finally:
                file.write_bytes(originals[m["path"]])
            outcome = {"fail": "killed", "pass": "survived", "timeout": "timeout"}[status]
            results.append({k: v for k, v in m.items() if not k.startswith("_")} |
                           {"result": outcome, "seconds": round(secs, 1)})
            print(f"[{i}/{len(chosen)}] {outcome:8} {m['path']}:{m['line']} {m['operator']}", file=sys.stderr)
    finally:
        for path, data in originals.items():
            f = workdir / path
            if f.is_file() and f.read_bytes() != data:
                f.write_bytes(data)
        if cleanup:
            cleanup()

    killed = sum(r["result"] in ("killed", "timeout") for r in results)
    survived = [r for r in results if r["result"] == "survived"]
    report = {"range": diff_range, "test": args.test, "clean_run_seconds": round(base_secs, 1),
              "candidates": len(all_mutants), "run": len(results), "killed": killed,
              "survived": len(survived), "score": round(killed / len(results), 2) if results else None,
              "mutants": results}
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report written to {args.out}", file=sys.stderr)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    print(f"Mutation pass over {diff_range}: {len(results)} of {len(all_mutants)} candidate mutants run,"
          f" {killed} caught by the tests, {len(survived)} survived.")
    if len(results) >= 5 and len(survived) == len(results):
        print("\nWARNING: every mutant survived. Check that the tests run the mutated copy at all: an"
              " editable install, a prebuilt binary or an absolute import path can point them at another"
              " checkout. In Python, run 'python -m pytest' from the repo root so the local package wins.")
    if survived:
        print("\nSurvivors (the tests pass with this bug planted):")
        for r in survived:
            print(f"\n  {r['path']}:{r['line']}  [{r['operator']}]")
            print(f"    was: {r['original'][:140]}")
            print(f"    now: {r['mutated'][:140]}")
    else:
        print("Every planted bug was caught.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
