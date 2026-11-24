"""Checks the release notes of a milestone and the milestone file before the package goes out.

Run from the repository root:
    python .claude/skills/milestone-package/check_release.py v0.3.0            # package stage
    python .claude/skills/milestone-package/check_release.py v0.3.0 --release  # after the tag is set

It checks that docs/releases/<tag>.md follows the template (title, date and commit lines, the five
sections in order, none empty), that the releases index has a row for the tag, and lists the
milestone's open acceptance criteria and checklist lines. With --release the tag must exist and
every box of the milestone file must be ticked or annotated with a dated note. Prints OK, or the
problems, and exits with 1 on a problem. Links are left to the docs-and-comments checker.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

RELEASES = Path("docs/releases")
MILESTONES = Path("docs/planning/milestones")
SECTIONS = [
    "What works",
    "How to verify",
    "Measurements",
    "Known limitations",
    "Changes since the previous milestone",
]
TITLE = re.compile(r"^# (v\d+\.\d+\.\d+) — M(\d): .+")
OPEN_BOX = re.compile(r"^- \[ \] (.*)")
# An open box is explained when it carries a dated note in brackets, as the milestone files do.
DATED_NOTE = re.compile(r"\(.*\d{4}-\d{2}-\d{2}.*\)")


def check_notes(tag: str) -> list[str]:
    """Template checks on docs/releases/<tag>.md."""
    path = RELEASES / f"{tag}.md"
    if not path.exists():
        return [f"{path} does not exist"]
    lines = path.read_text(encoding="utf-8").splitlines()
    problems = []
    title = TITLE.match(lines[0]) if lines else None
    if not title or title[1] != tag:
        problems.append(f"{path}: the first line must be '# {tag} — Mn: <milestone name>'")
    for field in ("- Date: ", "- Commit: "):
        if not any(line.startswith(field) for line in lines[:6]):
            problems.append(f"{path}: missing '{field.strip()}' line in the header")

    found = [(i, line[3:].strip()) for i, line in enumerate(lines) if line.startswith("## ")]
    names = [name for _, name in found]
    if [n for n in names if n in SECTIONS] != SECTIONS:
        problems.append(f"{path}: sections must be, in this order: {', '.join(SECTIONS)} (found: {', '.join(names)})")
    for index, (start, name) in enumerate(found):
        end = found[index + 1][0] if index + 1 < len(found) else len(lines)
        if name in SECTIONS and not any(line.strip() for line in lines[start + 1 : end]):
            problems.append(f"{path}: section '{name}' is empty")
    return problems


def check_index(tag: str) -> list[str]:
    """The releases README lists the tag in its index table."""
    readme = (RELEASES / "README.md").read_text(encoding="utf-8")
    if not re.search(rf"^\| `{re.escape(tag)}` \|", readme, re.MULTILINE):
        return [f"{RELEASES / 'README.md'}: no index row for `{tag}`"]
    return []


def milestone_file(tag: str) -> Path | None:
    """The milestone file whose row in the milestones README names the tag."""
    for line in (MILESTONES / "README.md").read_text(encoding="utf-8").splitlines():
        if f"`{tag}`" in line and (match := re.search(r"\]\(([^)]+\.md)\)", line)):
            return MILESTONES / match[1]
    return None


def open_boxes(path: Path) -> list[tuple[str, bool]]:
    """Open boxes of the milestone file, each with whether it carries a dated note."""
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if match := OPEN_BOX.match(line):
            result.append((match[1], bool(DATED_NOTE.search(match[1]))))
    return result


def tag_commit(tag: str) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{tag}^{{commit}}"], capture_output=True, text=True
    )
    return completed.stdout.strip() or None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tag", help="for example v0.3.0")
    parser.add_argument("--release", action="store_true", help="the tag is set: require it and no unexplained open box")
    args = parser.parse_args()

    problems = check_notes(args.tag) + check_index(args.tag)

    milestone = milestone_file(args.tag)
    if milestone is None or not milestone.exists():
        problems.append(f"{MILESTONES / 'README.md'}: no milestone row with `{args.tag}` and an existing file")
    else:
        boxes = open_boxes(milestone)
        print(f"{milestone}: {len(boxes)} open box(es)")
        for text, noted in boxes:
            print(f"  [{'noted' if noted else 'NO NOTE'}] {text[:110]}")
        if args.release:
            problems += [f"{milestone}: open box without a dated note: {text[:80]}" for text, noted in boxes if not noted]

    commit = tag_commit(args.tag)
    print(f"tag {args.tag}: {commit or 'not set'}")
    if args.release and commit is None:
        problems.append(f"tag {args.tag} does not exist (the author sets it after the merge)")

    if problems:
        print("\n".join(problems))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
