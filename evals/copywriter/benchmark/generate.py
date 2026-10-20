#!/usr/bin/env python3
"""Generate benchmark copy with Claude Code, without the skill (condition A) and with it (B).

Each brief in briefs.json is run N times per condition through `claude -p` in its own scratch
folder:
  A (without_skill): skills disabled (--disable-slash-commands), plain brief.
  B (with_skill):    a copy of the skill in the scratch folder's .claude/skills/, brief sent as
                     "/copywriter <brief>" so the skill is loaded for sure. This measures what the
                     skill does to the output, not whether it triggers.
MCP servers are skipped (--strict-mcp-config) and both conditions get the same model and tools.
Runs that already have output are skipped, so the script can be re-run to resume.

Usage:
    python generate.py --briefs briefs.json --skill ../../../skills/copywriter --out RUN_DIR
                       [--samples 2] [--model claude-opus-5-5] [--parallel 3] [--only web-1,email-2]
Outputs: RUN_DIR/raw/<id>__<condition>__<n>.json (CLI JSON incl. usage and cost) and
         RUN_DIR/text/<id>__<condition>__<n>.txt (the reply text).
Needs the `claude` CLI, logged in. Standard library only.
"""
import argparse
import concurrent.futures as cf
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

CONDITIONS = ("without_skill", "with_skill")


def run_one(job, args):
    brief, cond, n = job["brief"], job["cond"], job["n"]
    out_dir = Path(args.out)
    stem = f"{brief['id']}__{cond}__{n}"
    text_path = out_dir / "text" / f"{stem}.txt"
    if text_path.exists() and text_path.stat().st_size > 0:
        return stem, "skipped (exists)"
    work = out_dir / "_work" / stem
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    cmd = ["claude", "-p", "--output-format", "json", "--model", args.model, "--strict-mcp-config",
           "--no-session-persistence", "--permission-mode", "acceptEdits",
           "--allowedTools", "Read", "Glob", "Grep", "Write", "Edit", "Bash(python *)", "Bash(python3 *)", "Bash(py *)"]
    prompt = brief["prompt"]
    if cond == "with_skill":
        shutil.copytree(args.skill, work / ".claude" / "skills" / Path(args.skill).name)
        prompt = f"/{Path(args.skill).name} {prompt}"
    else:
        cmd.append("--disable-slash-commands")
    started = time.time()
    try:
        proc = subprocess.run(cmd, input=prompt, cwd=work, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=args.timeout)
    except subprocess.TimeoutExpired:
        return stem, f"timeout after {args.timeout}s"
    elapsed = round(time.time() - started, 1)
    (out_dir / "raw").mkdir(parents=True, exist_ok=True)
    (out_dir / "text").mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        (out_dir / "raw" / f"{stem}.err.txt").write_text(proc.stdout + "\n---\n" + proc.stderr, encoding="utf-8")
        return stem, f"failed (exit {proc.returncode}); see raw/{stem}.err.txt"
    data["_meta"] = {"brief_id": brief["id"], "condition": cond, "sample": n, "model": args.model,
                     "seconds": elapsed, "cmd": cmd[:3] + ["..."]}
    (out_dir / "raw" / f"{stem}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    result = data.get("result") or ""
    if data.get("is_error") or not result.strip():
        return stem, f"error: {str(result)[:200]}"
    text_path.write_text(result.strip() + "\n", encoding="utf-8")
    return stem, f"ok in {elapsed}s"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate benchmark copy with and without the skill via `claude -p`.")
    ap.add_argument("--briefs", required=True)
    ap.add_argument("--skill", required=True, help="path to the skill folder (e.g. skills/copywriter)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples", type=int, default=2)
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=1200, help="seconds per run")
    ap.add_argument("--only", help="comma-separated brief ids")
    ap.add_argument("--conditions", default=",".join(CONDITIONS))
    args = ap.parse_args(argv)
    if shutil.which("claude") is None:
        sys.exit("The `claude` CLI was not found on PATH.")
    briefs = json.loads(Path(args.briefs).read_text(encoding="utf-8"))
    if args.only:
        keep = set(args.only.split(","))
        briefs = [b for b in briefs if b["id"] in keep]
    jobs = [{"brief": b, "cond": c, "n": n} for b in briefs for c in args.conditions.split(",")
            for n in range(1, args.samples + 1)]
    print(f"{len(jobs)} runs ({len(briefs)} briefs x {args.conditions} x {args.samples}), model {args.model}", flush=True)
    with cf.ThreadPoolExecutor(max_workers=args.parallel) as pool:
        for stem, status in pool.map(lambda j: run_one(j, args), jobs):
            print(f"  {stem}: {status}", flush=True)
    print(f"Outputs in {Path(args.out).resolve() / 'text'} (raw CLI JSON in {Path(args.out).resolve() / 'raw'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
