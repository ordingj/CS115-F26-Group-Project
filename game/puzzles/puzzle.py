"""Shared clue helpers for Final Exam: Room 314.

This module owns the shared active-clue storage and direction-matching
utilities reused by the intersection, bathroom, and janitor puzzle domains.
All randomised results are stored in ``GameState`` so the event system and
command handlers can read them without re-rolling.

Step-specific clue ownership now lives in :mod:`game.puzzles.intersection`,
:mod:`game.puzzles.bathroom`, and :mod:`game.puzzles.janitor`.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from game.state import GameState

_TURN_DIRECTIONS: tuple[str, str] = ("left", "right")


def roll_active_clue(state: GameState, clue_key: str, options: Sequence[str]) -> str:
    """Pick one option at random, store it under *clue_key*, and return it.

    Parameters
    ----------
    state : GameState
        The live game state whose ``active_clues`` dict is updated in-place.
    clue_key : str
        The key under which the selected value is stored.
    options : Sequence[str]
        Non-empty sequence of candidate clue values.

    Returns
    -------
    str
        The randomly selected clue value.
    """
    value = random.choice(options)
    state.active_clues[clue_key] = value
    return value


def roll_turn_direction(state: GameState, clue_key: str) -> str:
    """Randomly choose left or right, persist it under *clue_key*, return it.

    Parameters
    ----------
    state : GameState
        The live game state whose ``active_clues`` dict is updated in-place.
    clue_key : str
        The key under which the chosen direction is stored in
        ``state.active_clues`` (e.g. ``"step2_mirror_dir"``).

    Returns
    -------
    str
        Either ``"left"`` or ``"right"``.
    """
    return roll_active_clue(state, clue_key, _TURN_DIRECTIONS)


def active_clue_value(state: GameState, clue_key: str) -> str:
    """Return one stored clue value, or an empty string when that clue is unset.

    Parameters
    ----------
    state : GameState
        The live game state to read from.
    clue_key : str
        Key to look up in ``state.active_clues``.

    Returns
    -------
    str
        The stored clue string, or ``""`` when *clue_key* is absent.
    """
    return str(state.active_clues.get(clue_key, ""))


def clue_direction_matches(direction: str, state: GameState, clue_key: str) -> bool:
    """Return ``True`` when *direction* matches the stored clue under *clue_key*.

    Parameters
    ----------
    direction : str
        Direction string to test (e.g. ``"left"``).
    state : GameState
        The live game state to read from.
    clue_key : str
        Key to look up in ``state.active_clues``.

    Returns
    -------
    bool
        ``True`` if the stored clue equals *direction*, ``False`` otherwise.
    """
    return direction == active_clue_value(state, clue_key)
