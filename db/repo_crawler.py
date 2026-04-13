"""
Run this for specific directory
python3 repo_crawler.py /path/to/your/repo
ex : python3 repo_crawler.py C:/PROJECT/UST/IDBMS/backend -o structure.txt
"""

import os
from pathlib import Path

def build_tree(root_path: Path, prefix: str = ""):
    """Recursively builds a directory tree structure as a list of strings."""
    lines = []
    entries = sorted(root_path.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    total = len(entries)

    for index, entry in enumerate(entries):
        connector = "└── " if index == total - 1 else "├── "
        lines.append(prefix + connector + entry.name)

        if entry.is_dir():
            extension = "    " if index == total - 1 else "│   "
            lines.extend(build_tree(entry, prefix + extension))

    return lines


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Save directory tree to a file")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the repository (default: current directory)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="tree.txt",
        help="Output file name (default: tree.txt)",
    )

    args = parser.parse_args()
    root = Path(args.path).resolve()

    if not root.exists():
        print(f"Error: Path '{root}' does not exist.")
        return

    lines = [root.name]
    lines.extend(build_tree(root))

    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Directory tree saved to: {output_path}")


if __name__ == "__main__":
    main()