"""Checks that the documentation hangs together: links, folder READMEs and module docstrings.

Run from the repository root: python .claude/skills/docs-and-comments/check_docs.py
Exits with 1 and lists every problem; prints OK otherwise. Standard library only.

1. Every relative Markdown link points to an existing file, and a `#anchor` to an existing heading.
2. Every folder under docs/ and every package under finsync/ has a README.md, and each docs README
   links every Markdown file and subfolder next to it. A docs folder of dated reports may instead be
   indexed file by file in its parent's README (docs/evaluation/results).
3. Every module under finsync/ starts with a docstring that says what it is for.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

SKIP_PARTS = {"node_modules", ".git", ".venv", "__pycache__", "dist", "build", ".gradle", ".idea"}
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def _markdown_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if not SKIP_PARTS & set(p.parts))


def _slug(heading: str) -> str:
    """GitHub's anchor for a heading: lower case, punctuation dropped, spaces to hyphens."""
    text = re.sub(r"`([^`]*)`", r"\1", heading)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def _anchors(path: Path, cache: dict[Path, set[str]]) -> set[str]:
    if path not in cache:
        seen: dict[str, int] = {}
        anchors: set[str] = set()
        in_fence = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if FENCE.match(line):
                in_fence = not in_fence
            match = None if in_fence else HEADING.match(line)
            if match:
                slug = _slug(match.group(2))
                count = seen.get(slug, 0)
                seen[slug] = count + 1
                anchors.add(slug if count == 0 else f"{slug}-{count}")
        cache[path] = anchors
    return cache[path]


def _links(path: Path) -> list[tuple[int, str]]:
    found, in_fence = [], False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            stripped = re.sub(r"`[^`]*`", "", line)
            found += [(number, target) for target in LINK.findall(stripped)]
    return found


def check_links(root: Path) -> list[str]:
    problems, cache = [], {}
    for path in _markdown_files(root):
        for number, target in _links(path):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("//"):
                continue  # external (https:, mailto:)
            file_part, _, anchor = target.partition("#")
            destination = (path.parent / unquote(file_part)).resolve() if file_part else path.resolve()
            where = f"{path.relative_to(root)}:{number}"
            if not destination.exists():
                problems.append(f"{where}: broken link {target}")
            elif anchor and destination.suffix == ".md" and anchor.lower() not in _anchors(destination, cache):
                problems.append(f"{where}: no heading for #{anchor} in {file_part or path.name}")
    return problems


def check_readmes(root: Path) -> list[str]:
    problems = []
    folders = [p for p in (root / "docs").rglob("*") if p.is_dir() and not SKIP_PARTS & set(p.parts)]
    packages = [p.parent for p in (root / "finsync").rglob("__init__.py") if not SKIP_PARTS & set(p.parts)]
    for folder in sorted({root / "docs", *folders, *packages}):
        readme = folder / "README.md"
        if not readme.exists():
            # A folder of dated reports may be indexed by its parent's README instead (docs/evaluation/results).
            parent_links = {unquote(t.partition("#")[0]) for _, t in _links(folder.parent / "README.md")} \
                if (folder.parent / "README.md").exists() else set()
            missing = [p.name for p in folder.glob("*.md") if f"{folder.name}/{p.name}" not in parent_links]
            if folder in packages or not any(folder.glob("*.md")) or missing:
                problems.append(f"{folder.relative_to(root)}: no README.md"
                                + (f", and the parent README does not link {', '.join(sorted(missing))}" if missing else ""))
            continue
        if folder in packages:
            continue
        linked = {unquote(t.partition("#")[0]).rstrip("/") for _, t in _links(readme)}
        for entry in sorted(folder.iterdir()):
            listed = entry.name in linked or f"{entry.name}/README.md" in linked
            if entry.name != "README.md" and (entry.suffix == ".md" or entry.is_dir()) and not listed:
                problems.append(f"{readme.relative_to(root)}: does not link {entry.name}")
    return problems


def check_docstrings(root: Path) -> list[str]:
    problems = []
    for path in sorted((root / "finsync").rglob("*.py")):
        if SKIP_PARTS & set(path.parts) or path.name == "__init__.py" and not path.read_text(encoding="utf-8").strip():
            continue
        text = path.read_text(encoding="utf-8").lstrip()
        if not (text.startswith('"""') or text.startswith("'''")):
            problems.append(f"{path.relative_to(root)}: no module docstring")
    return problems


def main() -> int:
    root = Path.cwd()
    problems = check_links(root) + check_readmes(root) + check_docstrings(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} problem(s).")
        return 1
    print("OK: links, folder READMEs and module docstrings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
