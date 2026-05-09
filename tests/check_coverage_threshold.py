"""Enforce a minimum per-file coverage threshold for runtime modules."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path

from coverage import Coverage


def _unique_paths(raw_paths: Iterable[str]) -> list[Path]:
    """Return the given file paths once each, preserving input order."""
    paths: list[Path] = []
    seen: set[Path] = set()
    for raw_path in raw_paths:
        path = Path(raw_path)
        if path in seen:
            continue
        seen.add(path)
        paths.append(path)
    return paths


def _coverage_percent(cov: Coverage, path: Path) -> float:
    """Return the measured statement coverage percentage for one file."""
    _filename, statements, _excluded, missing, _formatted = cov.analysis2(str(path))
    if not statements:
        return 100.0
    covered_statements = len(statements) - len(missing)
    return 100.0 * covered_statements / len(statements)


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, check coverage for each path, and return a shell status."""
    parser = argparse.ArgumentParser(
        description="Fail when any checked file is below the requested coverage threshold."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Source files whose statement coverage should be enforced.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=80.0,
        help="Minimum required statement coverage percentage for every file.",
    )
    args = parser.parse_args(argv)

    cov = Coverage()
    cov.load()

    failures: list[tuple[Path, float]] = []
    for path in _unique_paths(args.paths):
        percent = _coverage_percent(cov, path)
        if percent < args.threshold:
            failures.append((path, percent))

    if failures:
        print(f"Coverage threshold failures (<{args.threshold:.1f}%):")
        for path, percent in failures:
            print(f"  {path}: {percent:.1f}%")
        return 1

    print(f"All checked files meet the {args.threshold:.1f}% coverage threshold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
