#!/usr/bin/env python
"""Clean Python caches and run Django migration commands safely.

Normal use does not delete migration files::

    python scripts/migrations_cleanup.py

To regenerate application migration files, explicitly opt in::

    python scripts/migrations_cleanup.py --reset-migrations --yes

The reset mode preserves every migrations/__init__.py file and never deletes
the database. Do not use reset mode on a shared or production database.
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANAGE_PY = PROJECT_ROOT / "manage.py"
SKIPPED_PARTS = {".git", ".venv", "venv", "node_modules", "build"}


def remove_readonly(function: object, path: str, _error: object) -> None:
    """Allow cache cleanup when Windows marks a generated file read-only."""
    os.chmod(path, stat.S_IWRITE)
    function(path)  # type: ignore[operator]


def is_project_path(path: Path) -> bool:
    """Return True only for paths inside this project."""
    try:
        path.resolve().relative_to(PROJECT_ROOT)
        return True
    except ValueError:
        return False


def clean_python_cache() -> tuple[int, int]:
    removed_dirs = 0
    removed_files = 0
    for path in sorted(PROJECT_ROOT.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if any(part in SKIPPED_PARTS for part in path.relative_to(PROJECT_ROOT).parts):
            continue
        if path.is_dir() and path.name == "__pycache__":
            shutil.rmtree(path, onerror=remove_readonly)
            removed_dirs += 1
        elif path.is_file() and path.suffix in {".pyc", ".pyo"}:
            path.chmod(stat.S_IWRITE)
            path.unlink()
            removed_files += 1
    return removed_dirs, removed_files


def generated_migration_files() -> list[Path]:
    files: list[Path] = []
    for migrations_dir in PROJECT_ROOT.rglob("migrations"):
        if not migrations_dir.is_dir():
            continue
        relative_parts = migrations_dir.relative_to(PROJECT_ROOT).parts
        if any(part in SKIPPED_PARTS for part in relative_parts):
            continue
        files.extend(
            path
            for path in migrations_dir.glob("*.py")
            if path.name != "__init__.py" and is_project_path(path)
        )
    return sorted(files)


def run_manage_py(command: str) -> None:
    subprocess.run(
        [sys.executable, str(MANAGE_PY), command],
        cwd=PROJECT_ROOT,
        check=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove Python cache files, then create and apply Django migrations."
    )
    parser.add_argument(
        "--reset-migrations",
        action="store_true",
        help="Delete generated project migration .py files before makemigrations.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm the destructive --reset-migrations operation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not MANAGE_PY.is_file():
        raise SystemExit(f"manage.py was not found at {MANAGE_PY}")

    if args.reset_migrations and not args.yes:
        raise SystemExit("Migration reset cancelled. Add --yes only after backing up your database.")

    cache_dirs, cache_files = clean_python_cache()
    print(f"Removed {cache_dirs} __pycache__ directories and {cache_files} loose cache files.")

    if args.reset_migrations:
        migrations = generated_migration_files()
        for migration in migrations:
            print(f"Deleting {migration.relative_to(PROJECT_ROOT)}")
            migration.unlink()
        print(f"Deleted {len(migrations)} generated migration files; __init__.py files were preserved.")

    run_manage_py("makemigrations")
    run_manage_py("migrate")
    run_manage_py("check")
    print("Migration maintenance completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
