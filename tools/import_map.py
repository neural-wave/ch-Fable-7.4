"""Import map of the submission: which package uses which, as a Mermaid graph, and a check of the layers.

Every package may import only the packages below it in LAYERS; a top-level module counts as its own layer.
The script prints the graph (paste it into ARCHITECTURE.md) and exits with 1 on an import that goes up.

Usage (from the repository root):  python -B tools/import_map.py my_solution
"""
import ast
import collections
import pathlib
import sys

LAYERS = ["conventions", "core", "legacy", "insurance", "accounting", "reports", "export", "billing", "maturity", "submission"]


def unit(path, root):
    """The package of a file, or the module name of a top-level file."""
    parts = path.relative_to(root).parts
    return parts[0] if len(parts) > 1 else path.stem


def imported(path):
    """First components of the names a file imports."""
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module.split(".")[0]


def main(root):
    edges = collections.Counter()
    for path in sorted(root.rglob("*.py")):
        source = unit(path, root)
        edges.update((source, target) for target in imported(path) if target in LAYERS and target != source)
    print("```mermaid\nflowchart BT")
    for (source, target), count in sorted(edges.items()):
        print(f"    {source} -->|{count}| {target}")
    print("```")
    upward = [(s, t) for s, t in edges if LAYERS.index(t) > LAYERS.index(s)]
    for source, target in upward:
        print(f"layer violation: {source} imports {target}", file=sys.stderr)
    return 1 if upward else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "my_solution")))
