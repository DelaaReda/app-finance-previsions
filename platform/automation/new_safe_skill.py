#!/usr/bin/env python3
"""
Create a new skill from the safe skill template.

Usage:
  python3 scripts/new_safe_skill.py --name my-skill
  python3 scripts/new_safe_skill.py --name my-skill --description "Short trigger description"
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "skills" / "safe-skill-template"
SKILLS_DIR = ROOT / "skills"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    if not value:
        raise ValueError("Invalid skill name after normalization.")
    return value


def patch_skill_md(path: Path, name: str, description: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace("name: safe-skill-template", f"name: {name}")
    text = text.replace(
        "description: Build new skills with secure defaults (no hidden outbound actions, no hardcoded targets, explicit env gating). Use when creating or adapting skills from external sources.",
        f"description: {description}",
    )
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a new skill from safe template.")
    parser.add_argument("--name", required=True, help="New skill name (will be slugified).")
    parser.add_argument(
        "--description",
        default="Secure skill template instance. Update this description with concrete trigger conditions.",
        help="Frontmatter description for the new skill.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite if destination exists.")
    args = parser.parse_args()

    if not TEMPLATE_DIR.exists():
        raise SystemExit(f"Template not found: {TEMPLATE_DIR}")

    name = slugify(args.name)
    dst = SKILLS_DIR / name

    if dst.exists():
        if not args.force:
            raise SystemExit(f"Destination exists: {dst} (use --force to overwrite)")
        shutil.rmtree(dst)

    shutil.copytree(TEMPLATE_DIR, dst)
    patch_skill_md(dst / "SKILL.md", name=name, description=args.description.strip())

    print(f"Created: {dst}")
    print(f"Next: python3 {dst / 'scripts' / 'audit_skill.py'} --skill-dir {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

