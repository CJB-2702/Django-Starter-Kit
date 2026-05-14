#!/usr/bin/env python3
"""App-scoped context extractor. Wraps get_classes_and_descriptions for Django apps.

Usage:
    python get_models_and_control.py --application events
    python get_models_and_control.py --application administration --models_only
    python get_models_and_control.py --application events --file out.yaml
"""

import argparse
import sys
from pathlib import Path

# Ensure dev_tools is importable
sys.path.insert(0, str(Path(__file__).parent))
from get_classes_and_descriptions import build_context  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract class context from a Django application directory."
    )
    parser.add_argument(
        "--application",
        required=True,
        help="Application directory name under app/ (e.g. events, administration)",
    )
    parser.add_argument(
        "--models_only",
        action="store_true",
        help="Only scan the models/ sub-folder",
    )
    parser.add_argument("--file", help="Output file path (default: stdout)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    app_dir = project_root / "app" / args.application

    if not app_dir.exists():
        print(
            f"Error: application directory not found: app/{args.application}",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.models_only:
        target = app_dir / "models"
        if not target.exists():
            print(
                f"Error: models directory not found: app/{args.application}/models",
                file=sys.stderr,
            )
            sys.exit(1)
        display_path = f"app/{args.application}/models"
    else:
        target = app_dir
        display_path = f"app/{args.application}"

    try:
        output = build_context(str(target), display_path=display_path)
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
