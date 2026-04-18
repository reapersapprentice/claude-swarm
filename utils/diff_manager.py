"""Unified diff generation and patch application helpers."""

from __future__ import annotations

import difflib
from typing import List


def generate_unified_diff(original: str, updated: str, fromfile: str = "before", tofile: str = "after") -> str:
    """Generate unified diff text between two strings."""
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        updated.splitlines(keepends=True),
        fromfile=fromfile,
        tofile=tofile,
    )
    return "".join(diff)


def apply_unified_diff(original: str, diff_text: str) -> str:
    """Apply a unified diff to original text and return updated text."""
    original_lines = original.splitlines(keepends=True)
    patched: List[str] = []
    cursor = 0
    diff_lines = diff_text.splitlines(keepends=True)

    for line in diff_lines:
        if line.startswith("@@") or line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith(" "):
            patched.append(line[1:])
            cursor += 1
        elif line.startswith("-"):
            cursor += 1
        elif line.startswith("+"):
            patched.append(line[1:])

    if cursor < len(original_lines):
        patched.extend(original_lines[cursor:])
    return "".join(patched)
