"""Puzzle logic for Final Exam: Room 314.

Each puzzle step is self-contained here so the modules that use it (engine,
main) stay readable.  All randomised results are stored in ``GameState`` so
the event system and command handlers can read them without re-rolling.

Active-clue keys used by each step
───────────────────────────────────
Step 1 (4-way intersection):
    ``step1_correct_dir``   – "forward" | "left" | "right"
    ``step1_clue_type``     – "light" | "sign" | "shadow"

Step 2 (bathroom mirror):
    ``step2_mirror_dir``    – "left" | "right"

Step 3/4 (janitor song):
    ``step3_song_title``    – song title string
    ``step3_song_chorus``   – lyric line containing the direction word
    ``step3_correct_dir``   – "left" | "right"
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from game import load_yaml_data
from game.state import GameState


def _load_songs() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return ``(left_songs, right_songs)`` loaded from ``data/songs.yaml``.

    Songs are partitioned by their ``direction`` field in the YAML.  Each
    element of the returned lists is a ``(title, chorus)`` pair, where
    ``chorus`` is the lyric line that contains the direction keyword.

    Returns
    -------
    tuple[list[tuple[str, str]], list[tuple[str, str]]]
        Two parallel lists: first for "left" songs, second for "right" songs.
    """
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

_PUZZLE: dict = load_yaml_data("puzzle.yaml")
_TURN_DIRECTIONS: tuple[str, str] = ("left", "right")


def _roll_active_clue(state: GameState, clue_key: str, options: Sequence[str]) -> str:
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


def _roll_turn_direction(state: GameState, clue_key: str) -> str:
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
    return _roll_active_clue(state, clue_key, _TURN_DIRECTIONS)


def _active_clue_value(state: GameState, clue_key: str) -> str:
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
    return direction == _active_clue_value(state, clue_key)


# ── Step 1 – 4-way intersection ───────────────────────────────────────────────

_STEP1_DIRS: list[str] = ["forward", "left", "right"]

# Clue templates loaded from data/puzzle.yaml — keyed by clue_type.
# {correct} = correct direction; {opposite} = opposite direction.
_STEP1_CLUE_TEMPLATES: dict[str, str] = _PUZZLE["step1_clue_templates"]

_OPPOSITE: dict[str, str] = {
    "forward": "back",
    "back": "forward",
    "left": "right",
    "right": "left",
}

# Precomputed key list so step1_roll avoids rebuilding it on every roll.
_STEP1_CLUE_TYPES: list[str] = list(_STEP1_CLUE_TEMPLATES)


def step1_roll(state: GameState) -> None:
    """Randomly assign a correct direction and clue type for the 4-way intersection.

    Selects one direction from ``["forward", "left", "right"]`` and one clue
    type from the templates in ``data/puzzle.yaml``.  Results are written to
    ``state.active_clues`` under ``"step1_correct_dir"`` and
    ``"step1_clue_type"``.

    Call this every time the player enters (or re-enters) the intersection so
    the clue changes on each attempt, preventing memorisation.

    Parameters
    ----------
    state : GameState
        The live game state whose ``active_clues`` dict is updated in-place.
    """
    _roll_active_clue(state, "step1_correct_dir", _STEP1_DIRS)
    _roll_active_clue(state, "step1_clue_type", _STEP1_CLUE_TYPES)


def step1_clue_text(state: GameState) -> str:
    """Return the formatted clue string for the current Step 1 roll.

    Substitutes the ``{correct}`` and ``{opposite}`` placeholders in the
    template string chosen by :func:`step1_roll`.

    Parameters
    ----------
    state : GameState
        The live game state to read clue keys from.

    Returns
    -------
    str
        Human-readable clue sentence, or an empty string if
        :func:`step1_roll` has not been called yet.
    """
    correct_dir = _active_clue_value(state, "step1_correct_dir")
    clue_type = _active_clue_value(state, "step1_clue_type")
    template = _STEP1_CLUE_TEMPLATES.get(clue_type, "")
    if not (correct_dir and template):
        return ""
    opposite_dir = _OPPOSITE.get(correct_dir, "")
    return template.format(correct=correct_dir, opposite=opposite_dir)


# ── Step 2 – bathroom mirror ───────────────────────────────────────────────────


def step2_roll(state: GameState) -> None:
    """Randomly assign ``"left"`` or ``"right"`` as the bathroom mirror direction.

    The result is stored in ``state.active_clues["step2_mirror_dir"]``.
    Call this when the player first enters the bathroom for Step 2.

    Parameters
    ----------
    state : GameState
        The live game state whose ``active_clues`` dict is updated in-place.
    """
    _roll_turn_direction(state, "step2_mirror_dir")


def step2_mirror_text(state: GameState) -> str:
    """Return what the bathroom mirror shows after the player washes their hands.

    The mirror displays the direction backwards (e.g. ``"TFEL OG"`` for
    ``"GO LEFT"``) along with an unreflected direction label so the player
    can decode it.  Returns an empty string before Step 2 is rolled.

    Parameters
    ----------
    state : GameState
        The live game state containing the ``"step2_mirror_dir"`` clue.

    Returns
    -------
    str
        Multi-line string with the mirror visual, or ``""`` if not yet rolled.
    """
    direction = _active_clue_value(state, "step2_mirror_dir")
    if not direction:
        return ""
    # Backwards text effect: the mirror shows "TFEL OG" or "THGIR OG"
    backwards = ("GO " + direction.upper())[::-1]
    return _PUZZLE["step2_mirror_text"].format(
        backwards=backwards, direction=direction.upper()
    )


# ── Step 3/4 – janitor song ────────────────────────────────────────────────────

# Song pools are loaded from data/songs.yaml at import time.
# Each entry: (title, chorus_line) – chorus contains the direction word.


def step3_roll(state: GameState) -> None:
    """Randomly select a song and implied direction for the janitor encounter.

    Chooses a direction (left or right), then picks a random ``(title,
    chorus)`` pair from the matching song pool loaded from
    ``data/songs.yaml``.  Results are stored in ``state.active_clues``
    under ``"step3_correct_dir"``, ``"step3_song_title"``, and
    ``"step3_song_chorus"``.

    Parameters
    ----------
    state : GameState
        The live game state whose ``active_clues`` dict is updated in-place.
    """
    direction = _roll_turn_direction(state, "step3_correct_dir")
    pool = _LEFT_SONGS if direction == "left" else _RIGHT_SONGS
    title, chorus = random.choice(pool)
    state.active_clues["step3_song_title"] = title
    state.active_clues["step3_song_chorus"] = chorus
