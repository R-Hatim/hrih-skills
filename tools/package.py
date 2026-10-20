#!/usr/bin/env python3
"""Package skills as uploadable .skill files (zip archives) in dist/.

Usage:
    python tools/package.py            # all skills
    python tools/package.py <name>...  # specific skills

Each archive contains the skill folder at its root (<name>/SKILL.md, ...), the
layout claude.ai and the Claude desktop app expect when you upload a skill.
Compiled Python files are left out. Run tools/validate.py first.
"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
DIST = ROOT / "dist"
SKIP_DIRS = {"__pycache__", "node_modules", ".git"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def package(skill: Path) -> Path:
    DIST.mkdir(exist_ok=True)
    out = DIST / f"{skill.name}.skill"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(skill.rglob("*")):
            rel = f.relative_to(skill)
            if f.is_dir() or SKIP_DIRS & set(rel.parts) or f.suffix in SKIP_SUFFIXES:
                continue
            z.write(f, Path(skill.name) / rel)
    return out


def main() -> int:
    names = sys.argv[1:]
    skills = [SKILLS / n for n in names] if names else sorted(p for p in SKILLS.iterdir() if p.is_dir())
    for skill in skills:
        if not (skill / "SKILL.md").is_file():
            print(f"skip  {skill.name} (no SKILL.md)")
            continue
        out = package(skill)
        print(f"built {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
