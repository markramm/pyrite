"""
Test that the pyrite package has no circular import cycles.

This test uses AST parsing to build an import graph and detect cycles,
serving as both a test and validation for the pre-commit hook.
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path

import pytest

PYRITE_ROOT = Path(__file__).parent.parent / "pyrite"


def _build_import_graph(root: Path) -> dict[str, set[str]]:
    """Build a directed graph of intra-package imports using AST parsing."""
    graph: dict[str, set[str]] = defaultdict(set)

    for py_file in root.rglob("*.py"):
        # Module name relative to package root's parent
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

        # Only consider top-level imports (not inside functions/methods)
        for node in ast.iter_child_nodes(tree):
            # Top-level statements and class bodies
            import_nodes = []
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_nodes.append(node)
            elif isinstance(node, ast.ClassDef):
                # Include class-level imports too
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.Import, ast.ImportFrom)):
                        import_nodes.append(child)
            elif isinstance(node, ast.If):
                # Skip TYPE_CHECKING blocks — they're not runtime imports
                if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                    continue
                for child in ast.walk(node):
                    if isinstance(child, (ast.Import, ast.ImportFrom)):
                        import_nodes.append(child)
            elif isinstance(node, ast.Try):
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
                        # Relative import — resolve to absolute
                        pkg_parts = module_name.split(".")
                        base = pkg_parts[: -imp.level] if imp.level <= len(pkg_parts) else []
                        if imp.module:
                            base.append(imp.module)
                        target = ".".join(base)
                        if target.startswith("pyrite."):
                            graph[module_name].add(target)

    return dict(graph)


def _find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
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
                # Found a cycle
                idx = path.index(neighbor)
                cycle = path[idx:] + [neighbor]
                cycles.append(cycle)

        path.pop()
        rec_stack.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node)

    return cycles


class TestImportCycles:
    """Verify no circular import cycles exist in the pyrite package."""

    def test_no_import_cycles(self):
        """The pyrite package should have no circular import dependencies."""
        graph = _build_import_graph(PYRITE_ROOT)
        cycles = _find_cycles(graph)

        if cycles:
            # Format cycle info for readable error message
            cycle_strs = []
            for cycle in cycles[:5]:  # Show at most 5
                cycle_strs.append(" → ".join(cycle))
            msg = f"Found {len(cycles)} import cycle(s):\n" + "\n".join(cycle_strs)
            pytest.fail(msg)

    def test_import_graph_is_nonempty(self):
        """Sanity check: the import graph should contain pyrite modules."""
        graph = _build_import_graph(PYRITE_ROOT)
        assert len(graph) > 10, f"Expected many modules, got {len(graph)}"
        assert any(k.startswith("pyrite.") for k in graph), "No pyrite modules found"
