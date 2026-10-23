#!/usr/bin/env python3
"""Validate every skill in skills/ against the Agent Skills SKILL.md rules.

Usage:
    python tools/validate.py            # all skills
    python tools/validate.py <name>...  # specific skills

Checks, per skill folder:
  - exactly one SKILL.md, starting with YAML frontmatter that parses
  - only allowed keys: name, description, license, allowed-tools, metadata, compatibility
  - name: kebab-case, <= 64 chars, no leading/trailing/double hyphens, matches the folder name
  - description: present, <= 1024 chars, no angle brackets
  - compatibility (optional): string <= 500 chars
  - no __pycache__ or .pyc files committed inside the skill
Exits non-zero if any skill fails. Requires PyYAML (`pip install pyyaml`).
"""
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
ALLOWED = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
# Files copied into several skills (each skill installs on its own); every copy must match.
SHARED = ["scripts/lessons.py", "scripts/diff_facts.py", "references/lessons.md"]


def check(skill: Path) -> list[str]:
    errors = []
    skill_md = skill / "SKILL.md"
    if not skill_md.is_file():
        return ["SKILL.md not found"]
    extra = [p for p in skill.rglob("SKILL.md") if p != skill_md and "__pycache__" not in p.parts]
    if extra:
        errors.append(f"more than one SKILL.md: {', '.join(str(p.relative_to(skill)) for p in extra)}")
    if any(skill.rglob("__pycache__")) or any(skill.rglob("*.pyc")):
        errors.append("compiled Python files (__pycache__/*.pyc) inside the skill")

    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    if not m:
        return errors + ["missing or malformed YAML frontmatter"]
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        return errors + [f"invalid YAML in frontmatter: {e}"]
    if not isinstance(fm, dict):
        return errors + ["frontmatter must be a YAML mapping"]

    unexpected = set(fm) - ALLOWED
    if unexpected:
        errors.append(f"unexpected frontmatter keys: {', '.join(sorted(unexpected))}")

    name = fm.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("missing 'name'")
    else:
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
            errors.append(f"name '{name}' must be kebab-case (a-z, 0-9, single hyphens)")
        if len(name) > 64:
            errors.append(f"name is {len(name)} chars (max 64)")
        if name != skill.name:
            errors.append(f"name '{name}' doesn't match folder '{skill.name}'")

    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        errors.append("missing 'description'")
    else:
        if len(desc.strip()) > 1024:
            errors.append(f"description is {len(desc.strip())} chars (max 1024)")
        if "<" in desc or ">" in desc:
            errors.append("description contains angle brackets")

    comp = fm.get("compatibility")
    if comp is not None and (not isinstance(comp, str) or len(comp) > 500):
        errors.append("compatibility must be a string of at most 500 chars")
    return errors


def main() -> int:
    names = sys.argv[1:]
    skills = [SKILLS / n for n in names] if names else sorted(p for p in SKILLS.iterdir() if p.is_dir())
    if not skills:
        print("No skills found in skills/")
        return 1
    failed = 0
    for skill in skills:
        errors = check(skill) if skill.is_dir() else ["folder not found"]
        if errors:
            failed += 1
            print(f"FAIL  {skill.name}")
            for e in errors:
                print(f"      - {e}")
        else:
            print(f"ok    {skill.name}")
    print(f"\n{len(skills) - failed}/{len(skills)} skills valid")

    drift = 0
    for rel in SHARED:
        copies = {p: p.read_bytes() for p in sorted(SKILLS.glob(f"*/{rel}"))}
        if len(set(copies.values())) > 1:
            drift += 1
            print(f"FAIL  shared file {rel} differs between: "
                  + ", ".join(p.parent.parent.name if p.parent.name in ('scripts', 'references') else p.name
                              for p in copies))
    return 1 if failed or drift else 0


if __name__ == "__main__":
    sys.exit(main())
