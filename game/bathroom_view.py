"""Bathroom Step 2 read-only helpers for Final Exam: Room 314.

This module owns the non-mutating presentation layer of the handwashing
puzzle: sink inspection text, ambient bathroom status, the exit blocker
message, and mirror clue visibility.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial
from typing import Any

from game.command import RoomStateHandler, state_only_room_state_handler
from game.puzzle import step2_mirror_text
from game.room import Room
from game.state import GameState


@dataclass(frozen=True)
class _BathroomPuzzleState:
    """Snapshot of the Step 2 bathroom puzzle state used by helper functions."""

    phase: int
    sink_running: bool
    soap_applied: bool
    hands_washed: bool


@dataclass(frozen=True)
class _BathroomResponseKeys:
    """Read-only response keys implied by one Step 2 bathroom snapshot."""

    sink_key: str
    status_key: str = ""
    exit_block_key: str | None = None


def _attribute_int(room: Room, key: str, default: int = 0) -> int:
    """Return one integer-like room attribute, falling back to *default*."""
    value = room.attributes.get(key, default)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    return default


def _wash_phase(room: Room) -> int:
    """Return the current Step 2 wash phase, defaulting to ``0`` if unset."""
    return _attribute_int(room, "wash_phase")


def _bathroom_puzzle_state(room: Room, state: GameState) -> _BathroomPuzzleState:
    """Return the current Step 2 state derived from room attributes and flags."""
    return _BathroomPuzzleState(
        phase=_wash_phase(room),
        sink_running=bool(room.attributes.get("sink_running", False)),
        soap_applied=bool(room.attributes.get("soap_applied")),
        hands_washed=state.has_flag("step2_hands_washed"),
    )


def _display_response_keys(puzzle_state: _BathroomPuzzleState) -> _BathroomResponseKeys:
    """Return the read-only response keys implied by one Step 2 snapshot.

    The bathroom sink inspection text, ambient bathroom status line, and the
    movement blocker message shown when trying to leave early are all derived
    from the same wash phase, sink-running state, soap flag, and clean-hands
    flag. Keeping those key decisions in one helper prevents the read-only
    Step 2 surfaces from drifting apart as the state machine evolves.
    """
    if puzzle_state.hands_washed:
        return _BathroomResponseKeys("sink_clean", "clean", None)

    exit_block_key = (
        "hands_still_soapy" if puzzle_state.phase in (1, 2) else "hands_not_washed"
    )

    if puzzle_state.sink_running:
        sink_key = (
            "sink_running_rinse"
            if puzzle_state.phase in (0, 2)
            else "sink_running_stop"
        )
        if puzzle_state.phase == 0:
            status_key = "soapy" if puzzle_state.soap_applied else "soap_needed"
            return _BathroomResponseKeys(sink_key, status_key, exit_block_key)
        if puzzle_state.phase == 2:
            return _BathroomResponseKeys(sink_key, "water_back", exit_block_key)
        if puzzle_state.phase == 3:
            return _BathroomResponseKeys(sink_key, "final_rinse", exit_block_key)
        return _BathroomResponseKeys(sink_key, "", exit_block_key)
    status_key = "water_cut" if puzzle_state.phase == 1 else ""
    return _BathroomResponseKeys("sink_off", status_key, exit_block_key)


def _room_response_keys(room: Room, state: GameState) -> _BathroomResponseKeys:
    """Return the read-only Step 2 response keys for one room/state snapshot."""
    return _display_response_keys(_bathroom_puzzle_state(room, state))


def _current_bathroom_response_keys(
    room: Room,
    state: GameState,
) -> _BathroomResponseKeys | None:
    """Return read-only Step 2 response keys only when *room* is the bathroom."""
    if room.room_id != "bathroom":
        return None
    return _room_response_keys(room, state)


def bathroom_exit_block_message(
    room: Room, state: GameState, move_responses: Mapping[str, str]
) -> str | None:
    """Return an exit-blocking message while hands are not yet clean."""
    response_keys = _current_bathroom_response_keys(room, state)
    if response_keys is None:
        return None
    if response_keys.exit_block_key is None:
        return None
    return move_responses[response_keys.exit_block_key]


def bathroom_mirror_text(state: GameState, fogged_message: str) -> str:
    """Return the mirror clue text, gated on the handwashing puzzle being complete."""
    if not state.has_flag("step2_hands_washed"):
        return fogged_message
    return step2_mirror_text(state)


def bathroom_sink_text(
    room: Room, state: GameState, look_responses: Mapping[str, str]
) -> str:
    """Return the current sink description for bathroom observation commands."""
    response_keys = _room_response_keys(room, state)
    return look_responses[response_keys.sink_key]


def bathroom_status_text(
    room: Room, state: GameState, status_responses: Mapping[str, str]
) -> str:
    """Return the ambient bathroom clue/status text for room rendering."""
    response_keys = _current_bathroom_response_keys(room, state)
    if response_keys is None:
        return ""
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
