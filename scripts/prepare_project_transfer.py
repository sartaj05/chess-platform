from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GENERATED_DIRECTORIES = (
    ".dart-local",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".vscode",
    ".idea",
    ".venv",
    "venv",
    "htmlcov",
    "staticfiles",
    "mobile_app/.dart_tool",
    "mobile_app/.idea",
    "mobile_app/build",
    "mobile_app/android/.gradle",
)
GENERATED_FILES = (
    ".coverage",
    "mobile_app/.flutter-plugins-dependencies",
    "mobile_app/android/local.properties",
    "mobile_app/android/chess_platform_mobile_android.iml",
    "mobile_app/chess_platform_mobile.iml",
)
LOCAL_DATA_FILES = ("db.sqlite3",)
PRIVATE_FILES = (
    ".env",
    ".env.production",
    "mobile_app/android/key.properties",
    "mobile_app/android/store-password.dpapi",
    "mobile_app/android/key-password.dpapi",
)
PRIVATE_DIRECTORIES = ("secrets",)
PROTECTED_PATHS = (
    "mobile_app/android/app/release-keystore.jks",
    "backups",
    "media",
    "db.sqlite3 (unless --local-data is explicitly used)",
)


def is_inside_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def generated_paths() -> list[Path]:
    direct = [
        path.resolve()
        for path in (ROOT / item for item in GENERATED_DIRECTORIES + GENERATED_FILES)
        if path.exists()
    ]
    discovered = []
    for pattern in ("__pycache__", "*.pyc", "*.pyo", "*.log"):
        discovered.extend(ROOT.rglob(pattern))

    def covered_by_direct_directory(path: Path) -> bool:
        return any(base.is_dir() and (path == base or base in path.parents) for base in direct)

    paths = direct + [
        path.resolve()
        for path in discovered
        if path.exists() and not covered_by_direct_directory(path.resolve())
    ]
    unique = set(paths)
    directories = {path for path in unique if path.is_dir()}
    return sorted(
        path
        for path in unique
        if not any(parent in directories for parent in path.parents)
    )


def private_paths() -> list[Path]:
    paths = [ROOT / item for item in PRIVATE_FILES + PRIVATE_DIRECTORIES]
    return sorted(path.resolve() for path in paths if path.exists())


def remove(path: Path) -> None:
    if not is_inside_root(path):
        raise RuntimeError(f"Refusing path outside project: {path}")
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safely remove reproducible local files before transferring Chess Platform."
    )
    parser.add_argument("--apply", action="store_true", help="Delete generated files shown by the dry run.")
    parser.add_argument(
        "--private-config",
        action="store_true",
        help="Also remove local environment files and secrets from this copy.",
    )
    parser.add_argument(
        "--local-data",
        action="store_true",
        help="Also remove the local SQLite development database.",
    )
    parser.add_argument(
        "--i-have-a-backup",
        action="store_true",
        help="Required confirmation when --private-config is used.",
    )
    args = parser.parse_args()
    if (args.private_config or args.local_data) and not args.i_have_a_backup:
        parser.error("--private-config and --local-data require --i-have-a-backup")

    targets = generated_paths()
    if args.private_config:
        targets.extend(private_paths())
    if args.local_data:
        targets.extend(
            (ROOT / item).resolve()
            for item in LOCAL_DATA_FILES
            if (ROOT / item).exists()
        )
    mode = "DELETE" if args.apply else "DRY RUN"
    print(f"Chess Platform transfer cleanup - {mode}")
    for path in sorted(set(targets)):
        print(f"  {path.relative_to(ROOT)}")
    print("Protected and never deleted:")
    for item in PROTECTED_PATHS:
        print(f"  {item}")
    if not args.apply:
        print("No files changed. Run again with --apply after reviewing this list.")
        return 0
    for path in sorted(set(targets), key=lambda item: len(item.parts), reverse=True):
        if path.exists():
            remove(path)
    print(f"Removed {len(targets)} local/generated item(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
