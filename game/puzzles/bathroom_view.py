"""Bathroom Step 2 read-only helpers for Final Exam: Room 314.

This module owns the non-mutating presentation layer of the handwashing
puzzle: sink inspection text, ambient bathroom status, and mirror clue
visibility. It derives those responses from the shared Step 2 bathroom
state helpers owned by :mod:`game.bathroom`.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial
from typing import Any

from game import load_yaml_data
from game.puzzles.bathroom import bathroom_response_keys
from game.commands.command import RoomStateHandler, state_only_room_state_handler
from game.room import Room
from game.state import GameState

_PUZZLE: dict = load_yaml_data("puzzle.yaml")


def step2_mirror_text(state: GameState) -> str:
    """Return the revealed bathroom mirror clue text for Step 2."""
    direction = str(state.active_clues.get("step2_mirror_dir", ""))
    if not direction:
        return ""
    backwards = (_PUZZLE["step2_direction_prefix"] + direction.upper())[::-1]
    return _PUZZLE["step2_mirror_text"].format(
        backwards=backwards,
        direction=direction.upper(),
    )


def bathroom_mirror_text(state: GameState, fogged_message: str) -> str:
    """Return the mirror clue text, gated on the handwashing puzzle being complete."""
    if not state.has_flag("step2_hands_washed"):
        return fogged_message
    return step2_mirror_text(state)


def bathroom_sink_text(
    room: Room, state: GameState, look_responses: Mapping[str, str]
) -> str:
    """Return the current sink description for bathroom observation commands."""
    response_keys = bathroom_response_keys(room, state)
    return look_responses[response_keys.sink_key]


def bathroom_status_text(
    room: Room, state: GameState, status_responses: Mapping[str, str]
) -> str:
    """Return the ambient bathroom clue/status text for room rendering."""
    if room.room_id != "bathroom":
        return ""
    response_keys = bathroom_response_keys(room, state)
    return (
        status_responses[response_keys.status_key] if response_keys.status_key else ""
    )


def bathroom_look_target_handlers(
    commands: Mapping[str, Any],
) -> dict[tuple[str, str], RoomStateHandler]:
    """Return bathroom room-target handlers for ``look`` and ``examine`` verbs.

    Parameters
    ----------
    commands : Mapping[str, Any]
        Top-level command-response mapping loaded from ``commands.yaml``.

    Returns
    -------
    dict[tuple[str, str], RoomStateHandler]
        Mapping of ``(room_id, target)`` to bathroom-specific look handlers.
    """
    look_responses = commands["look"]
    return {
        ("bathroom", "mirror"): state_only_room_state_handler(
            partial(
                bathroom_mirror_text,
                fogged_message=look_responses["mirror_fogged"],
            )
        ),
        ("bathroom", "sink"): partial(
            bathroom_sink_text,
            look_responses=look_responses,
        ),
    }


def bathroom_read_target_handlers(
    commands: Mapping[str, Any],
) -> dict[tuple[str, str], RoomStateHandler]:
    """Return bathroom room-target handlers for the ``read`` verb.

    Parameters
    ----------
    commands : Mapping[str, Any]
        Top-level command-response mapping loaded from ``commands.yaml``.

    Returns
    -------
    dict[tuple[str, str], RoomStateHandler]
        Mapping of ``(room_id, target)`` to bathroom-specific read handlers.
    """
    read_responses = commands["read"]
    return {
        ("bathroom", "mirror"): state_only_room_state_handler(
            partial(
                bathroom_mirror_text,
                fogged_message=read_responses["mirror_fogged"],
            )
        )
    }
