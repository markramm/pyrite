#!/usr/bin/env python3
"""Detect circular import cycles in the pyrite package.

Used as a pre-commit hook. Exits non-zero if cycles are found.
Only considers top-level imports (function-scoped lazy imports are safe).
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path

PYRITE_ROOT = Path(__file__).parent.parent / "pyrite"


def build_import_graph(root: Path) -> dict[str, set[str]]:
    """Build a directed graph of top-level intra-package imports."""
    graph: dict[str, set[str]] = defaultdict(set)

    for py_file in root.rglob("*.py"):
        try:
            rel = py_file.relative_to(root.parent)
        except ValueError:
            continue
        parts = list(rel.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        module_name = ".".join(parts)
        if not module_name:
            continue

        try:
            tree = ast.parse(py_file.read_text(), filename=str(py_file))
        except SyntaxError:
            continue

        for node in ast.iter_child_nodes(tree):
            import_nodes = []
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_nodes.append(node)
            elif isinstance(node, ast.ClassDef):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.Import, ast.ImportFrom)):
                        import_nodes.append(child)
            elif isinstance(node, (ast.If, ast.Try)):
                for child in ast.walk(node):
                    if isinstance(child, (ast.Import, ast.ImportFrom)):
                        import_nodes.append(child)

            for imp in import_nodes:
                if isinstance(imp, ast.Import):
                    for alias in imp.names:
                        if alias.name.startswith("pyrite."):
                            graph[module_name].add(alias.name)
                elif isinstance(imp, ast.ImportFrom):
                    if imp.module and imp.module.startswith("pyrite."):
                        graph[module_name].add(imp.module)
                    elif imp.level and imp.level > 0:
                        pkg_parts = module_name.split(".")
                        base = pkg_parts[: -imp.level] if imp.level <= len(pkg_parts) else []
                        if imp.module:
                            base.append(imp.module)
                        target = ".".join(base)
                        if target.startswith("pyrite."):
                            graph[module_name].add(target)

    return dict(graph)


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Find all cycles in a directed graph using DFS."""
    cycles = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                idx = path.index(neighbor)
                cycles.append(path[idx:] + [neighbor])

        path.pop()
        rec_stack.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node)

    return cycles


def main():
    graph = build_import_graph(PYRITE_ROOT)
    cycles = find_cycles(graph)

    if cycles:
        print(f"Found {len(cycles)} import cycle(s):")
        for cycle in cycles[:10]:
            print(f"  {' → '.join(cycle)}")
        sys.exit(1)

    print(f"No import cycles found ({len(graph)} modules checked)")
    sys.exit(0)


if __name__ == "__main__":
    main()
