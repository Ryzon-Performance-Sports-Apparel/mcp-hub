#!/usr/bin/env python3
"""
fix-double-tags.py — Deduplicate duplicate `tags:` frontmatter keys.

The area-tagger-agent has a bug where it appends a new `tags: [...]` line
instead of merging into the existing `tags:\n  - ...` block. Result: many
.md files have TWO `tags:` keys in their YAML frontmatter, which makes
the YAML invalid (second wins, first is silently discarded).

This script finds affected files, merges both tag arrays, deduplicates,
and writes a single valid `tags:` field back.

Usage:
    python3 fix-double-tags.py --dry-run DIR [DIR ...]   # default, safe
    python3 fix-double-tags.py --write DIR [DIR ...]     # applies changes

Behavior:
- Scans recursively for .md files with frontmatter (starts with ---)
- If frontmatter contains TWO or more `tags:` keys (top-level YAML),
  extracts all tag values, merges, deduplicates, writes back with a
  SINGLE `tags:` block using inline-list syntax.
- Preserves all other frontmatter keys and their ordering.
- Preserves document body byte-for-byte.

Exit codes: 0 ok, 1 errors encountered.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


FRONTMATTER_DELIMITER = "---"


@dataclass
class FrontmatterResult:
    before_frontmatter: str
    frontmatter_raw: str
    after_frontmatter: str


def split_frontmatter(text: str) -> FrontmatterResult | None:
    """Return (before, frontmatter-inner, after) or None if no frontmatter."""
    if not text.startswith(FRONTMATTER_DELIMITER + "\n") and not text.startswith(
        FRONTMATTER_DELIMITER + "\r\n"
    ):
        return None
    # Find the closing delimiter
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != FRONTMATTER_DELIMITER:
        return None
    close_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == FRONTMATTER_DELIMITER:
            close_idx = i
            break
    if close_idx is None:
        return None
    before = lines[0]  # the opening ---
    frontmatter_raw = "".join(lines[1:close_idx])
    closing_and_after = "".join(lines[close_idx:])  # includes the closing ---
    return FrontmatterResult(
        before_frontmatter=before,
        frontmatter_raw=frontmatter_raw,
        after_frontmatter=closing_and_after,
    )


# Match a top-level `tags:` line. Top-level = no leading whitespace.
# Captures two styles:
#   1. inline array: tags: [a, b, c]
#   2. block list: tags:\n  - a\n  - b
TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_\-]*)\s*:", re.MULTILINE)


def parse_tag_values_from_block(
    frontmatter: str, key_start: int, key_line_end: int
) -> tuple[list[str], int]:
    """
    Given a frontmatter string and the span of a `tags:` line,
    return (values, end_offset_of_block) where end_offset is the index
    into frontmatter after the last line of this tags block (either the
    rest of the inline array line, or the last `- item` line).
    """
    tag_line = frontmatter[key_start:key_line_end]
    # Strip "tags:" prefix
    after_colon = tag_line.split(":", 1)[1].strip()

    if after_colon.startswith("["):
        # inline array — may span multiple lines if very long, but usually one line
        # find the closing bracket
        # We'll search from key_start
        bracket_depth = 0
        i = frontmatter.index("[", key_start)
        end = i
        while end < len(frontmatter):
            ch = frontmatter[end]
            if ch == "[":
                bracket_depth += 1
            elif ch == "]":
                bracket_depth -= 1
                if bracket_depth == 0:
                    end += 1
                    break
            end += 1
        inline = frontmatter[i:end]
        # Remove brackets
        inner = inline[1:-1]
        values = [v.strip().strip('"').strip("'") for v in inner.split(",")]
        values = [v for v in values if v]
        # advance past any trailing whitespace/newline on that line
        while end < len(frontmatter) and frontmatter[end] in (" ", "\t"):
            end += 1
        if end < len(frontmatter) and frontmatter[end] == "\n":
            end += 1
        return values, end

    if after_colon == "":
        # block style — look for subsequent lines that start with "- " or "  - "
        values: list[str] = []
        # Move past the "tags:" line
        pos = key_line_end
        while pos < len(frontmatter):
            line_end = frontmatter.find("\n", pos)
            if line_end == -1:
                line_end = len(frontmatter)
            line = frontmatter[pos:line_end]
            stripped = line.lstrip()
            if stripped.startswith("- "):
                value = stripped[2:].strip().strip('"').strip("'")
                if value:
                    values.append(value)
                pos = line_end + 1
                continue
            if line.strip() == "":
                pos = line_end + 1
                continue
            # non-blank, non-list-item → end of block
            break
        return values, pos

    # Unexpected inline scalar (e.g. "tags: foo") — treat as single value
    value = after_colon.strip().strip('"').strip("'")
    # advance past the line
    end = key_line_end
    if end < len(frontmatter) and frontmatter[end] == "\n":
        end += 1
    return ([value] if value else []), end


def find_tag_blocks(frontmatter: str) -> list[tuple[int, int, list[str]]]:
    """Find all top-level `tags:` blocks. Return list of (start, end, values)."""
    results: list[tuple[int, int, list[str]]] = []
    for match in TOP_LEVEL_KEY_RE.finditer(frontmatter):
        key = match.group(1)
        if key != "tags":
            continue
        line_start = match.start()
        # find end of this line
        line_end = frontmatter.find("\n", line_start)
        if line_end == -1:
            line_end = len(frontmatter)
        values, block_end = parse_tag_values_from_block(
            frontmatter, line_start, line_end
        )
        results.append((line_start, block_end, values))
    return results


def dedup_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def rewrite_frontmatter(frontmatter: str) -> tuple[str, bool]:
    """
    Return (new_frontmatter, changed). If multiple tags blocks exist,
    merge them into ONE inline-array block at the position of the FIRST.
    """
    blocks = find_tag_blocks(frontmatter)
    if len(blocks) < 2:
        return frontmatter, False

    merged_values = dedup_preserve_order([v for _, _, vals in blocks for v in vals])

    # Build replacement: a single `tags: [a, b, c]` line with terminating newline
    # Quote values that contain spaces or special chars
    def fmt(v: str) -> str:
        if any(c in v for c in (" ", ":", ",", "[", "]", "#", "&", "*", "!", "|")):
            escaped = v.replace('"', '\\"')
            return f'"{escaped}"'
        return v

    formatted = ", ".join(fmt(v) for v in merged_values)
    replacement = f"tags: [{formatted}]\n"

    # Remove all tag blocks from back to front (so offsets stay valid),
    # then insert replacement at the FIRST block's start position.
    first_start = blocks[0][0]
    out = frontmatter
    for start, end, _ in reversed(blocks):
        out = out[:start] + out[end:]
    out = out[:first_start] + replacement + out[first_start:]
    return out, True


def process_file(path: Path, write: bool) -> tuple[bool, str | None]:
    """Return (changed, error_message)."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        return False, f"Unicode decode error: {e}"
    except OSError as e:
        return False, f"Read error: {e}"

    fm = split_frontmatter(text)
    if fm is None:
        return False, None  # no frontmatter — skip quietly

    new_frontmatter, changed = rewrite_frontmatter(fm.frontmatter_raw)
    if not changed:
        return False, None

    new_text = fm.before_frontmatter + new_frontmatter + fm.after_frontmatter

    if write:
        try:
            path.write_text(new_text, encoding="utf-8")
        except OSError as e:
            return False, f"Write error: {e}"
    return True, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Report what would change, do not modify files (default)",
    )
    group.add_argument(
        "--write",
        action="store_true",
        help="Actually apply changes (mutates files)",
    )
    parser.add_argument(
        "paths",
        metavar="DIR",
        nargs="+",
        help="Directories to scan recursively",
    )
    args = parser.parse_args()

    write_mode = bool(args.write)
    mode_label = "WRITE" if write_mode else "DRY-RUN"

    total_scanned = 0
    total_changed = 0
    errors: list[tuple[Path, str]] = []
    changed_files: list[Path] = []

    for root_str in args.paths:
        root = Path(root_str).expanduser().resolve()
        if not root.exists():
            errors.append((root, "path does not exist"))
            continue
        if not root.is_dir():
            errors.append((root, "path is not a directory"))
            continue
        for md_file in root.rglob("*.md"):
            if md_file.is_file():
                total_scanned += 1
                changed, err = process_file(md_file, write=write_mode)
                if err:
                    errors.append((md_file, err))
                if changed:
                    total_changed += 1
                    changed_files.append(md_file)

    print(f"\n[{mode_label}] scanned {total_scanned} .md files")
    print(f"[{mode_label}] {total_changed} file(s) {'modified' if write_mode else 'would be modified'}")
    if changed_files:
        print("\nFiles:")
        for p in changed_files:
            print(f"  - {p}")
    if errors:
        print(f"\n{len(errors)} error(s):")
        for p, msg in errors:
            print(f"  ! {p}: {msg}", file=sys.stderr)
        return 1

    if not write_mode and total_changed > 0:
        print("\nRun with --write to apply the changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
