"""Dependency graph extraction utilities for Python source."""

from __future__ import annotations

import ast
from typing import Dict, List


def map_python_dependencies(source_code: str) -> Dict[str, List[str]]:
    """Extract imported module names from Python source code."""
    tree = ast.parse(source_code)
    imports: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return {"imports": sorted(set(imports))}
