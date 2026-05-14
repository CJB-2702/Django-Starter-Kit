#!/usr/bin/env python3
"""Extract class names and docstrings from a Python directory tree.

Usage:
    python get_classes_and_descriptions.py --path app/events/models
    python get_classes_and_descriptions.py --path app/events --file out.yaml
"""

import argparse
import ast
import json
import sys
from pathlib import Path


def _quote(s: str) -> str:
    """Return a YAML-safe scalar for a string value."""
    if s == "":
        return "''"
    specials = set(':#{}[]|>&*?!\'"\\,\t\r\n')
    reserved = {"true", "false", "null", "yes", "no", "on", "off"}
    if not any(c in specials for c in s) and s == s.strip() and s not in reserved:
        return s
    return json.dumps(s, ensure_ascii=False)


def _render_yaml(node: dict, level: int = 0) -> str:
    pad = "  " * level
    out = []

    out.append(f"{pad}path: {_quote(node['path'])}")

    if files := node.get("files"):
        out.append(f"{pad}files:")
        for f in files:
            out.append(f"{pad}  - name: {_quote(f['name'])}")
            if classes := f.get("classes"):
                out.append(f"{pad}    classes:")
                for cls in classes:
                    out.append(f"{pad}      - name: {_quote(cls['name'])}")
                    out.append(f"{pad}        docstring: {_quote(cls['docstring'])}")

    if subs := node.get("subdirectories"):
        out.append(f"{pad}subdirectories:")
        item_prefix = f"{pad}  - "
        for sub in subs:
            sub_lines = _render_yaml(sub, level + 2).split("\n")
            out.append(item_prefix + sub_lines[0].lstrip())
            out.extend(sub_lines[1:])

    return "\n".join(out)


def extract_classes(filepath: Path) -> list[dict]:
    """Parse a .py file and return its class names with docstrings."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            docstring = ast.get_docstring(node) or ""
            classes.append({"name": node.name, "docstring": docstring})
    return classes


def scan_directory(root: Path, display_path: str) -> dict:
    """Recursively scan a directory and build a tree dict."""
    result: dict = {"path": display_path}
    files: list[dict] = []
    subdirs: list[dict] = []

    try:
        entries = sorted(root.iterdir(), key=lambda p: (p.is_dir(), p.name))
    except PermissionError:
        return result

    for entry in entries:
        if entry.name.startswith("_"):
            continue

        if entry.is_file():
            if entry.suffix == ".py":
                file_entry: dict = {"name": entry.name}
                classes = extract_classes(entry)
                if classes:
                    file_entry["classes"] = classes
                files.append(file_entry)
            else:
                files.append({"name": entry.name})
        elif entry.is_dir():
            sub_path = f"{display_path}/{entry.name}"
            subdirs.append(scan_directory(entry, sub_path))

    if files:
        result["files"] = files
    if subdirs:
        result["subdirectories"] = subdirs

    return result


def build_context(path: str, display_path: str | None = None) -> str:
    """Main entry point: scan a path and return YAML string.

    display_path overrides the root label and prefix for all sub-paths in output.
    """
    root = Path(path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    if not root.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")

    label = display_path if display_path is not None else path.rstrip("/")
    tree = scan_directory(root, label)
    return _render_yaml(tree)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract class names and docstrings from a Python directory tree."
    )
    parser.add_argument("--path", required=True, help="Directory to scan")
    parser.add_argument("--file", help="Output file path (default: stdout)")
    args = parser.parse_args()

    try:
        output = build_context(args.path)
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.file:
        Path(args.file).write_text(output + "\n", encoding="utf-8")
        print(f"Written to {args.file}")
    else:
        print(output)


if __name__ == "__main__":
    main()
