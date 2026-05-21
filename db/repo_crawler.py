"""
Run this for specific directory:
python3 repo_crawler.py /path/to/your/repo
ex:
python3 repo_crawler.py C:/PROJECT/UST/IDBMS/backend -o structure.txt
python3 repo_crawler.py ~/NPI-IDBMS/backend -o structure.txt

Ignore files/folders:
python3 repo_crawler.py ~/NPI-IDBMS/backend -o structure.txt --ignore .venv __pycache__ .git
python3 repo_crawler.py ~/NPI-IDBMS/frontend -o structure.txt --ignore .venv __pycache__ .git node_modules
"""

from pathlib import Path


DEFAULT_IGNORE = {
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".DS_Store",
}


def should_ignore(path: Path, ignore_list: set[str]) -> bool:
    """
    Returns True if the file/folder should be ignored.
    Matches by name only, e.g. '.venv', '__pycache__', 'node_modules'.
    """
    return path.name in ignore_list


def build_tree(root_path: Path, prefix: str = "", ignore_list: set[str] | None = None):
    """Recursively builds a directory tree structure as a list of strings."""
    if ignore_list is None:
        ignore_list = DEFAULT_IGNORE

    lines = []

    entries = [
        entry
        for entry in root_path.iterdir()
        if not should_ignore(entry, ignore_list)
    ]

    entries = sorted(entries, key=lambda e: (e.is_file(), e.name.lower()))
    total = len(entries)

    for index, entry in enumerate(entries):
        connector = "└── " if index == total - 1 else "├── "
        lines.append(prefix + connector + entry.name)

        if entry.is_dir():
            extension = "    " if index == total - 1 else "│   "
            lines.extend(build_tree(entry, prefix + extension, ignore_list))

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

    parser.add_argument(
        "--ignore",
        nargs="*",
        default=[],
        help="Extra files/folders to ignore, e.g. --ignore .venv __pycache__ node_modules",
    )

    args = parser.parse_args()
    root = Path(args.path).resolve()

    if not root.exists():
        print(f"Error: Path '{root}' does not exist.")
        return

    ignore_list = DEFAULT_IGNORE.union(set(args.ignore))

    lines = [root.name]
    lines.extend(build_tree(root, ignore_list=ignore_list))

    output_path = Path(args.output)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Directory tree saved to: {output_path}")
    print(f"Ignored: {', '.join(sorted(ignore_list))}")


if __name__ == "__main__":
    main()