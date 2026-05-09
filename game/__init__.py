"""Shared package helpers for Final Exam: Room 314."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

_DATA_DIR = Path(__file__).parent.parent / "data"


def load_yaml_data(filename: str) -> dict[str, Any]:
    """Load a YAML mapping from the repository's shared data directory.

    All runtime modules use this single entry point so file-path resolution
    and YAML parsing logic stay centralised.  The ``data/`` directory is
    resolved relative to this file at import time, so the function works
    regardless of the current working directory.

    Parameters
    ----------
    filename : str
        Basename of the YAML file to load (e.g. ``"rooms.yaml"``).
        The file must exist under the project's ``data/`` directory.

    Returns
    -------
    dict[str, Any]
        The deserialised top-level mapping from the YAML document.

    Raises
    ------
    FileNotFoundError
        If *filename* does not exist under ``data/``.
    yaml.YAMLError
        If the file content is not valid YAML.
    """
    # Resolve path relative to the data/ directory and decode as UTF-8.
    return yaml.safe_load((_DATA_DIR / filename).read_text(encoding="utf-8"))


def format_indented_lines(
    lines: Iterable[str], *, limit: int | None = None, indent: str = "  "
) -> str:
    """Return one string with each selected line prefixed by *indent*.

    Parameters
    ----------
    lines : Iterable[str]
        Source lines to indent and join with newlines.
    limit : int or None, optional
        When provided, only the first *limit* lines are included.
    indent : str, optional
        Prefix added before every selected line. Defaults to two spaces.

    Returns
    -------
    str
        Newline-joined indented lines.
    """
    selected_lines = list(lines)
    if limit is not None:
        selected_lines = selected_lines[:limit]
    return "\n".join(f"{indent}{line}" for line in selected_lines)
