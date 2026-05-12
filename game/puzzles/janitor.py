"""Janitor song-clue helpers.

The janitor provides an ambient musical hint for Step 3 of the puzzle.
He hums louder (revealing more chorus lines) as the deadline approaches.
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from functools import partial
from typing import Any

from game import format_indented_lines, load_yaml_data
from game.commands.command import RoomStateCommandSpec
from game.puzzles.puzzle import roll_turn_direction
from game.room import Room
from game.state import GameState


def _load_songs() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return ``(left_songs, right_songs)`` loaded from ``data/songs.yaml``."""
    raw: dict = load_yaml_data("songs.yaml")
    left: list[tuple[str, str]] = []
    right: list[tuple[str, str]] = []
    for entry in raw["songs"]:
        pair = (entry["title"], entry["chorus"])
        if entry["direction"] == "left":
            left.append(pair)
        else:
            right.append(pair)
    return left, right


_LEFT_SONGS, _RIGHT_SONGS = _load_songs()


def step3_roll(state: GameState) -> None:
    """Randomly select the janitor song clue and store it in ``active_clues``."""
    direction = roll_turn_direction(state, "step3_correct_dir")
    pool = _LEFT_SONGS if direction == "left" else _RIGHT_SONGS
    title, chorus = random.choice(pool)
    state.active_clues["step3_song_title"] = title
    state.active_clues["step3_song_chorus"] = chorus


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


def _janitor_line_limit(state: GameState, *, full_chorus: bool) -> int | None:
    """Return the number of chorus lines to expose for the current janitor view.

    Parameters
    ----------
    state : GameState
        Current game state; provides ``time_remaining``.
    full_chorus : bool
        When ``True``, expose every chorus line regardless of urgency.

    Returns
    -------
    int or None
        ``1`` or ``2`` for the ambient timed hint tiers, or ``None`` when the
        full chorus should be shown.
    """
    if full_chorus:
        return None
    return (
        1 if state.time_remaining > 300 else (2 if state.time_remaining > 150 else None)
    )


def janitor_text(state: GameState, prefix: str, *, full_chorus: bool = False) -> str:
    """Return janitor chorus text for either the ambient hint or LISTEN command.

    The ambient hint reveals more of the chorus as the timer drops:

    - More than 300 seconds left: 1 line.
    - 151–300 seconds left: 2 lines.
    - 150 seconds or fewer: all lines.

    The ``LISTEN`` command bypasses those tiers and always shows the full
    chorus by passing ``full_chorus=True``.

    Parameters
    ----------
    state : GameState
        Current game state; provides ``time_remaining`` and ``active_clues``.
    prefix : str
        Header line prepended before the chorus lines.
    full_chorus : bool, optional
        When ``True``, return the complete chorus regardless of time remaining.

    Returns
    -------
    str
        Formatted multi-line chorus string, or ``""`` when no chorus is active.
    """
    return _janitor_text(
        state,
        prefix,
        limit=_janitor_line_limit(state, full_chorus=full_chorus),
    )


def _listen_in_janitor_hallway(
    room: Room,
    state: GameState,
    listen_responses: Mapping[str, str],
) -> str:
    """Return the janitor chorus and mark the song as heard when available."""
    heard_text = janitor_text(
        state,
        listen_responses["janitor_prefix"],
        full_chorus=True,
    )
    if not heard_text:
        return listen_responses["silence"]
    room.attributes["song_heard"] = True
    state.set_flag("step3_song_heard")
    return heard_text


def janitor_room_state_commands(
    commands: Mapping[str, Any],
) -> tuple[RoomStateCommandSpec, ...]:
    """Return declarative janitor command specs for player registration."""
    listen_responses = commands["listen"]
    return (
        (
            ("listen",),
            "hallway_janitor",
            listen_responses["silence"],
            partial(
                _listen_in_janitor_hallway,
                listen_responses=listen_responses,
            ),
        ),
    )
