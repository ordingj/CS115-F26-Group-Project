"""Bathroom Step 2 state and action helpers for Final Exam: Room 314.

This module owns the shared Step 2 bathroom puzzle snapshot, the
response-key mapping and exit-block rule derived from that snapshot, plus
the mutating handwashing state machine, which progresses through four
phases stored in ``room.attributes["wash_phase"]``:

- **Phase 0**: Soap not yet applied; sink off.
- **Phase 1**: Soap applied; player must stop the sink (not rinse yet).
- **Phase 2**: Sink stopped; player must rinse.
- **Phase 3**: Rinsed; player must stop the running sink.
- **Phase 4**: Hands washed — ``step2_hands_washed`` flag is set.

Read-only Step 2 presentation helpers in :mod:`game.puzzles.bathroom_view` reuse the
shared puzzle snapshot defined here so both modules read the same source of
truth for sink, soap, and completion state.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import partial
from typing import Any

from game.commands.command import RoomStateCommandSpec, fixed_room_state_handler
from game.puzzles.puzzle import roll_turn_direction
from game.room import Room
from game.state import GameState


@dataclass(frozen=True)
class BathroomPuzzleState:
    """Snapshot of the Step 2 bathroom puzzle state used by helper functions."""

    phase: int
    sink_running: bool
    soap_applied: bool
    hands_washed: bool


@dataclass(frozen=True)
class BathroomResponseKeys:
    """Response keys implied by one Step 2 bathroom puzzle snapshot."""

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


def bathroom_puzzle_state(room: Room, state: GameState) -> BathroomPuzzleState:
    """Return the current Step 2 state derived from room attributes and flags."""
    return BathroomPuzzleState(
        phase=_wash_phase(room),
        sink_running=bool(room.attributes.get("sink_running", False)),
        soap_applied=bool(room.attributes.get("soap_applied")),
        hands_washed=state.has_flag("step2_hands_washed"),
    )


def step2_roll(state: GameState) -> None:
    """Randomly assign the bathroom mirror direction for Step 2."""
    roll_turn_direction(state, "step2_mirror_dir")


def bathroom_response_keys(room: Room, state: GameState) -> BathroomResponseKeys:
    """Return the Step 2 response keys implied by one room/state snapshot."""
    puzzle_state = bathroom_puzzle_state(room, state)
    if puzzle_state.hands_washed:
        return BathroomResponseKeys("sink_clean", "clean", None)

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
            return BathroomResponseKeys(sink_key, status_key, exit_block_key)
        if puzzle_state.phase == 2:
            return BathroomResponseKeys(sink_key, "water_back", exit_block_key)
        if puzzle_state.phase == 3:
            return BathroomResponseKeys(sink_key, "final_rinse", exit_block_key)
        return BathroomResponseKeys(sink_key, "", exit_block_key)

    status_key = "water_cut" if puzzle_state.phase == 1 else ""
    return BathroomResponseKeys("sink_off", status_key, exit_block_key)


def bathroom_exit_block_message(
    room: Room,
    state: GameState,
    move_responses: Mapping[str, str],
) -> str | None:
    """Return an exit-blocking message while bathroom Step 2 is incomplete."""
    if room.room_id != "bathroom":
        return None
    response_keys = bathroom_response_keys(room, state)
    if response_keys.exit_block_key is None:
        return None
    return move_responses[response_keys.exit_block_key]


@dataclass(frozen=True)
class _BathroomActionTransition:
    """Describe one Step 2 action-driven phase transition and side effects."""

    response_key: str
    phase: int
    sink_running: bool | None = None
    reset_phase1_attempts: bool = False
    state_flags: tuple[str, ...] = ()


BathroomActionFallback = Callable[
    [Room, BathroomPuzzleState, Mapping[str, str]],
    str,
]
"""Callable type for one action-specific non-transition Step 2 response."""

BathroomActionGuard = Callable[
    [Room, BathroomPuzzleState, Mapping[str, str]],
    str | None,
]
"""Callable type for an optional pre-transition Step 2 action guard."""


_RINSE_TRANSITIONS: dict[int, _BathroomActionTransition] = {
    0: _BathroomActionTransition("phase_0", phase=1, sink_running=False),
    2: _BathroomActionTransition("phase_2", phase=3),
}

_STOP_TRANSITIONS: dict[int, _BathroomActionTransition] = {
    1: _BathroomActionTransition(
        "phase_1",
        phase=2,
        sink_running=True,
        reset_phase1_attempts=True,
    ),
    3: _BathroomActionTransition(
        "phase_3",
        phase=4,
        sink_running=False,
        state_flags=("step2_hands_washed", "step2_mirror_clue_visible"),
    ),
}


def _set_wash_phase(
    room: Room, phase: int, *, sink_running: bool | None = None
) -> None:
    """Persist a Step 2 wash phase and optionally the sink-running flag.

    Parameters
    ----------
    room : Room
        The bathroom room to mutate.
    phase : int
        New wash phase (0–4).
    sink_running : bool or None, optional
        When provided, also sets ``room.attributes["sink_running"]``.
    """
    room.attributes["wash_phase"] = phase
    if sink_running is not None:
        room.attributes["sink_running"] = sink_running


def _transition_response(
    room: Room,
    responses: Mapping[str, str],
    response_key: str,
    *,
    phase: int,
    sink_running: bool | None = None,
) -> str:
    """Advance the wash phase and return the matching response string.

    Combines :func:`_set_wash_phase` with a response lookup so callers
    don't need two lines for every phase transition.

    Parameters
    ----------
    room : Room
        The bathroom room to mutate.
    responses : Mapping[str, str]
        Response text dict (from ``commands.yaml`` for the relevant action).
    response_key : str
        Key to look up in *responses* after the transition.
    phase : int
        New wash phase.
    sink_running : bool or None, optional
        Forwarded to :func:`_set_wash_phase`.

    Returns
    -------
    str
        The response string for *response_key*.
    """
    _set_wash_phase(room, phase, sink_running=sink_running)
    return responses[response_key]


def _apply_action_transition(
    room: Room,
    state: GameState,
    responses: Mapping[str, str],
    transition: _BathroomActionTransition,
) -> str:
    """Apply one declared action transition and return its response text."""
    if transition.reset_phase1_attempts:
        room.attributes["rinse_phase1_attempts"] = 0
    response = _transition_response(
        room,
        responses,
        transition.response_key,
        phase=transition.phase,
        sink_running=transition.sink_running,
    )
    for flag in transition.state_flags:
        state.set_flag(flag)
    return response


def _already_clean_response(
    puzzle_state: BathroomPuzzleState, responses: Mapping[str, str]
) -> str | None:
    """Return an "already clean" message if hands are washed, otherwise ``None``.

    Parameters
    ----------
    puzzle_state : _BathroomPuzzleState
        Snapshot of the current Step 2 bathroom state.
    responses : Mapping[str, str]
        Response dict for the current action; must contain ``"already_clean"``.

    Returns
    -------
    str or None
        ``responses["already_clean"]`` when Step 2 is already complete;
        ``None`` otherwise.
    """
    if puzzle_state.hands_washed:
        return responses["already_clean"]
    return None


def _action_puzzle_state(
    room: Room, state: GameState, responses: Mapping[str, str]
) -> tuple[BathroomPuzzleState, str | None]:
    """Return the current Step 2 state plus any already-clean short-circuit.

    Action handlers for ``SOAP``, ``RINSE``, and ``STOP`` all begin by reading
    the shared bathroom puzzle snapshot and immediately returning the relevant
    ``already_clean`` response when the player has already finished Step 2.

    Parameters
    ----------
    room : Room
        The bathroom room whose attributes hold the Step 2 state.
    state : GameState
        Current game state.
    responses : Mapping[str, str]
        Response mapping for the current action.

    Returns
    -------
    tuple[BathroomPuzzleState, str or None]
        The shared puzzle snapshot plus the action-specific clean-hands
        response, if one applies.
    """
    puzzle_state = bathroom_puzzle_state(room, state)
    return puzzle_state, _already_clean_response(puzzle_state, responses)


def _action_response(
    room: Room,
    state: GameState,
    responses: Mapping[str, str],
    *,
    transitions: Mapping[int, _BathroomActionTransition],
    guard: BathroomActionGuard | None = None,
    fallback: BathroomActionFallback,
) -> str:
    """Resolve one Step 2 action through shared prechecks and transitions.

    All bathroom action handlers first short-circuit when hands are already
    clean, then apply any declared phase transition, then fall back to the
    action-specific non-transition response for the current state.

    Parameters
    ----------
    room : Room
        The bathroom room whose attributes hold the Step 2 state.
    state : GameState
        Current game state.
    responses : Mapping[str, str]
        Response mapping for the current action.
    transitions : Mapping[int, _BathroomActionTransition]
        Declared transitions keyed by wash phase.
    guard : BathroomActionGuard or None, optional
        Action-specific short-circuit run after the clean-hands check but
        before transition lookup.
    fallback : BathroomActionFallback
        Action-specific response builder used when no transition applies.

    Returns
    -------
    str
        The response text for the current action and puzzle state.
    """
    puzzle_state, clean_response = _action_puzzle_state(room, state, responses)
    if clean_response is not None:
        return clean_response
    if guard is not None:
        guard_response = guard(room, puzzle_state, responses)
        if guard_response is not None:
            return guard_response
    transition = transitions.get(puzzle_state.phase)
    if transition is not None:
        return _apply_action_transition(room, state, responses, transition)
    return fallback(room, puzzle_state, responses)


def _phase1_rinse_response(room: Room, responses: Mapping[str, str]) -> str:
    """Return the escalating wrong-rinse response while the sink is off."""
    attempts = _attribute_int(room, "rinse_phase1_attempts") + 1
    room.attributes["rinse_phase1_attempts"] = attempts
    key = (
        "phase_1_wrong_3"
        if attempts >= 3
        else "phase_1_wrong_2"
        if attempts == 2
        else "phase_1_wrong"
    )
    return responses[key]


def _rinse_fallback_response(
    room: Room,
    puzzle_state: BathroomPuzzleState,
    responses: Mapping[str, str],
) -> str:
    """Return the non-transition rinse response for one Step 2 state."""
    if puzzle_state.phase == 1:
        return _phase1_rinse_response(room, responses)
    return responses["phase_done"]


def _rinse_guard_response(
    _room: Room,
    puzzle_state: BathroomPuzzleState,
    responses: Mapping[str, str],
) -> str | None:
    """Reject Phase 0 rinsing until soap has been applied."""
    if puzzle_state.phase == 0 and not puzzle_state.soap_applied:
        return responses["no_soap"]
    return None


def _stop_fallback_response(
    _room: Room,
    puzzle_state: BathroomPuzzleState,
    responses: Mapping[str, str],
) -> str:
    """Return the non-transition stop-sink response for one Step 2 state."""
    if puzzle_state.phase == 0:
        return responses["phase_0"]
    return responses["fallback"]


def _soap_fallback_response(
    room: Room,
    puzzle_state: BathroomPuzzleState,
    responses: Mapping[str, str],
) -> str:
    """Return the soap-dispenser response for one Step 2 state."""
    if puzzle_state.soap_applied:
        return responses["already_applied"]
    if puzzle_state.phase != 0:
        return responses["wrong_phase"]
    room.attributes["soap_applied"] = True
    return responses["applied"]


def rinse_hands(
    room: Room, state: GameState, rinse_responses: Mapping[str, str]
) -> str:
    """Advance the handwashing puzzle when the player rinses their hands.

    Phase transitions triggered here:

    - **Phase 0 + soap**: → Phase 1 (sink off, soap not yet rinsed).
    - **Phase 2**: → Phase 3 (rinsing underway).
    - **Phase 1**: Wrong action — counter escalates hint text.

    Parameters
    ----------
    room : Room
        The bathroom room.
    state : GameState
        Current game state.
    rinse_responses : Mapping[str, str]
        Response strings for rinse outcomes.

    Returns
    -------
    str
        Appropriate response text for the current puzzle state.
    """
    return _action_response(
        room,
        state,
        rinse_responses,
        transitions=_RINSE_TRANSITIONS,
        guard=_rinse_guard_response,
        fallback=_rinse_fallback_response,
    )


def stop_sink(room: Room, state: GameState, stop_responses: Mapping[str, str]) -> str:
    """Advance the handwashing puzzle when the player turns off the sink.

    Phase transitions triggered here:

    - **Phase 1**: → Phase 2 (sink re-activated for rinsing).
    - **Phase 3**: → Phase 4 (hands washed; sets ``step2_hands_washed`` flag).

    Parameters
    ----------
    room : Room
        The bathroom room.
    state : GameState
        Current game state.
    stop_responses : Mapping[str, str]
        Response strings for stop-sink outcomes.

    Returns
    -------
    str
        Appropriate response text for the current puzzle state.
    """
    return _action_response(
        room,
        state,
        stop_responses,
        transitions=_STOP_TRANSITIONS,
        fallback=_stop_fallback_response,
    )


def apply_soap(room: Room, state: GameState, soap_responses: Mapping[str, str]) -> str:
    """Apply soap from the bathroom dispenser when the puzzle state allows it.

    Soap can only be applied in Phase 0 and only once; subsequent calls
    return ``already_applied``.

    Parameters
    ----------
    room : Room
        The bathroom room.
    state : GameState
        Current game state.
    soap_responses : Mapping[str, str]
        Response strings for soap-application outcomes.

    Returns
    -------
    str
        Appropriate response text for the current puzzle state.
    """
    return _action_response(
        room,
        state,
        soap_responses,
        transitions={},
        fallback=_soap_fallback_response,
    )


def bathroom_room_state_commands(
    commands: Mapping[str, Any],
) -> tuple[RoomStateCommandSpec, ...]:
    """Return declarative bathroom action command specs for player registration.

    Parameters
    ----------
    commands : Mapping[str, Any]
        Top-level command-response mapping loaded from ``commands.yaml``.

    Returns
    -------
    tuple[RoomStateCommandSpec, ...]
        Room-gated command specs for the bathroom action verbs.
    """
    return (
        (
            ("rinse", "wash"),
            "bathroom",
            commands["rinse"]["no_location"],
            partial(rinse_hands, rinse_responses=commands["rinse"]),
        ),
        (
            ("dry",),
            "bathroom",
            commands["dry"]["no_location"],
            fixed_room_state_handler(commands["dry"]["missing_handle"]),
        ),
        (
            ("stop",),
            "bathroom",
            commands["stop"]["no_location"],
            partial(stop_sink, stop_responses=commands["stop"]),
        ),
        (
            ("soap",),
            "bathroom",
            commands["soap"]["no_location"],
            partial(apply_soap, soap_responses=commands["soap"]),
        ),
    )
