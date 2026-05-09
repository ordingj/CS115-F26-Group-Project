"""Janitor song-clue formatting helpers.

The janitor provides an ambient musical hint for Step 3 of the puzzle.
He hums louder (revealing more chorus lines) as the deadline approaches.
"""

from __future__ import annotations

from game import format_indented_lines
from game.state import GameState


def _active_chorus_lines(state: GameState) -> list[str]:
    """Return the active janitor chorus as stripped lines, or an empty list.

    Parameters
    ----------
    state : GameState
        Current game state; reads ``active_clues["step3_song_chorus"]``.

    Returns
    -------
    list[str]
        Non-empty lines from the active chorus, or ``[]`` when absent.
    """
    chorus = state.active_clues.get("step3_song_chorus", "")
    return chorus.strip().splitlines() if chorus else []


def _janitor_text(state: GameState, prefix: str, *, limit: int | None = None) -> str:
    """Return one prefixed janitor clue block, or ``""`` when no chorus is active.

    Parameters
    ----------
    state : GameState
        Current game state providing the active chorus lines.
    prefix : str
        Header line prepended before the formatted chorus.
    limit : int or None, optional
        Maximum number of chorus lines to show. ``None`` keeps all lines.

    Returns
    -------
    str
        Prefixed, indented janitor clue text, or ``""`` when no chorus is
        active.
    """
    lines = _active_chorus_lines(state)
    if not lines:
        return ""
    return prefix + "\n" + format_indented_lines(lines, limit=limit)


def janitor_hint_text(state: GameState, prefix: str) -> str:
    """Return the ambient janitor hint, revealing more lines as time runs low.

    The number of chorus lines shown scales with urgency:

    - More than 300 seconds left: 1 line.
    - 151–300 seconds left: 2 lines.
    - 150 seconds or fewer: all lines.

    Parameters
    ----------
    state : GameState
        Current game state; provides ``time_remaining`` and ``active_clues``.
    prefix : str
        Header line (e.g. ``“The janitor is humming…”``) prepended before the lines.

    Returns
    -------
    str
        Formatted multi-line hint string, or ``""`` when no chorus is active.
    """
    count = (
        1 if state.time_remaining > 300 else (2 if state.time_remaining > 150 else None)
    )
    return _janitor_text(state, prefix, limit=count)


def janitor_listen_text(state: GameState, prefix: str) -> str:
    """Return the full janitor chorus used by the LISTEN command.

    Unlike :func:`janitor_hint_text`, this always shows all chorus lines
    regardless of time remaining.

    Parameters
    ----------
    state : GameState
        Current game state.
    prefix : str
        Header line prepended before the chorus.

    Returns
    -------
    str
        Formatted multi-line chorus string, or ``""`` when no chorus is active.
    """
    return _janitor_text(state, prefix)
