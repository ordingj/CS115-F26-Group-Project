"""Bathroom puzzle helpers for Final Exam: Room 314.

Handles the Step 2 handwashing state machine, which progresses through four
phases (0–4) stored in ``room.attributes["wash_phase"]``:

- **Phase 0**: Soap not yet applied; sink off.
- **Phase 1**: Soap applied; player must stop the sink (not rinse yet).
- **Phase 2**: Sink stopped; player must rinse.
- **Phase 3**: Rinsed; player must stop the running sink.
- **Phase 4**: Hands washed — ``step2_hands_washed`` flag is set.
"""

from __future__ import annotations

from collections.abc import Mapping

from game.puzzle import step2_mirror_text
from game.room import Room
from game.state import GameState


def _wash_phase(room: Room) -> int:
    """Return the current Step 2 wash phase, defaulting to ``0`` if unset.

    Parameters
    ----------
    room : Room
        The bathroom room whose ``attributes`` hold wash state.

    Returns
    -------
    int
        Current phase (0–4).
    """
    return int(room.attributes.get("wash_phase", 0))


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


def _already_clean_response(
    state: GameState, responses: Mapping[str, str]
) -> str | None:
    """Return an "already clean" message if hands are washed, otherwise ``None``.

    Parameters
    ----------
    state : GameState
        Current game state.
    responses : Mapping[str, str]
        Response dict for the current action; must contain ``"already_clean"``.

    Returns
    -------
    str or None
        ``responses["already_clean"]`` when Step 2 is already complete;
        ``None`` otherwise.
    """
    if state.has_flag("step2_hands_washed"):
        return responses["already_clean"]
    return None


def bathroom_exit_block_message(
    room: Room, state: GameState, move_responses: Mapping[str, str]
) -> str | None:
    """Return an exit-blocking message while hands are not yet clean.

    Movement commands call this before committing a move; a non-``None``
    return value tells the engine to show the message and stay in the bathroom.

    Parameters
    ----------
    room : Room
        The current room (returns ``None`` immediately if not ``"bathroom"``).
    state : GameState
        Current game state.
    move_responses : Mapping[str, str]
        Subset of ``commands.yaml`` movement response strings.

    Returns
    -------
    str or None
        Blocking message text, or ``None`` to allow movement.
    """
    if room.room_id != "bathroom" or state.has_flag("step2_hands_washed"):
        return None
    phase = _wash_phase(room)
    return (
        move_responses["hands_still_soapy"]
        if phase in (1, 2)
        else move_responses["hands_not_washed"]
    )


def bathroom_mirror_text(state: GameState, fogged_message: str) -> str:
    """Return the mirror clue text, gated on the handwashing puzzle being complete.

    Parameters
    ----------
    state : GameState
        Current game state.
    fogged_message : str
        Fallback text shown when the mirror is still fogged (Step 2 incomplete).

    Returns
    -------
    str
        The decoded clue string from :func:`~game.puzzle.step2_mirror_text`,
        or *fogged_message* if the player hasn't washed their hands yet.
    """
    if not state.has_flag("step2_hands_washed"):
        return fogged_message
    return step2_mirror_text(state)


def bathroom_sink_text(
    room: Room, state: GameState, look_responses: Mapping[str, str]
) -> str:
    """Return the current sink description for bathroom observation commands.

    Parameters
    ----------
    room : Room
        The bathroom room.
    state : GameState
        Current game state.
    look_responses : Mapping[str, str]
        Response strings for the various sink states.

    Returns
    -------
    str
        One of ``sink_clean``, ``sink_running_rinse``,
        ``sink_running_stop``, or ``sink_off``.
    """
    phase = _wash_phase(room)
    running = room.attributes.get("sink_running", False)
    if state.has_flag("step2_hands_washed"):
        return look_responses["sink_clean"]
    if running:
        key = "sink_running_rinse" if phase in (0, 2) else "sink_running_stop"
        return look_responses[key]
    return look_responses["sink_off"]


def bathroom_status_text(
    room: Room, state: GameState, status_responses: Mapping[str, str]
) -> str:
    """Return the ambient bathroom clue/status text for room rendering.

    Parameters
    ----------
    room : Room
        Current room; returns ``""`` immediately when not in the bathroom.
    state : GameState
        Current game state.
    status_responses : Mapping[str, str]
        Bathroom status strings from ``commands.yaml``.

    Returns
    -------
    str
        One of the configured bathroom status messages, or ``""`` when no
        status line applies.
    """
    if room.room_id != "bathroom":
        return ""
    phase = _wash_phase(room)
    running = room.attributes.get("sink_running", False)
    if state.has_flag("step2_hands_washed"):
        return status_responses["clean"]
    if running and phase == 0:
        if room.attributes.get("soap_applied"):
            return status_responses["soapy"]
        return status_responses["soap_needed"]
    if not running and phase == 1:
        return status_responses["water_cut"]
    if running and phase == 2:
        return status_responses["water_back"]
    if running and phase == 3:
        return status_responses["final_rinse"]
    return ""


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
    if (clean_response := _already_clean_response(state, rinse_responses)) is not None:
        return clean_response
    phase = _wash_phase(room)
    if phase == 0:
        if not room.attributes.get("soap_applied"):
            return rinse_responses["no_soap"]
        return _transition_response(
            room,
            rinse_responses,
            "phase_0",
            phase=1,
            sink_running=False,
        )
    if phase == 2:
        return _transition_response(room, rinse_responses, "phase_2", phase=3)
    if phase == 1:
        attempts = int(room.attributes.get("rinse_phase1_attempts", 0)) + 1
        room.attributes["rinse_phase1_attempts"] = attempts
        key = (
            "phase_1_wrong_3"
            if attempts >= 3
            else "phase_1_wrong_2"
            if attempts == 2
            else "phase_1_wrong"
        )
        return rinse_responses[key]
    return rinse_responses["phase_done"]


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
    if (clean_response := _already_clean_response(state, stop_responses)) is not None:
        return clean_response
    phase = _wash_phase(room)
    if phase == 1:
        room.attributes["rinse_phase1_attempts"] = 0
        return _transition_response(
            room,
            stop_responses,
            "phase_1",
            phase=2,
            sink_running=True,
        )
    if phase == 3:
        response = _transition_response(
            room,
            stop_responses,
            "phase_3",
            phase=4,
            sink_running=False,
        )
        state.set_flag("step2_hands_washed")
        state.set_flag("step2_mirror_clue_visible")
        return response
    if phase == 0:
        return stop_responses["phase_0"]
    return stop_responses["fallback"]


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
    if (clean_response := _already_clean_response(state, soap_responses)) is not None:
        return clean_response
    if room.attributes.get("soap_applied"):
        return soap_responses["already_applied"]
    if _wash_phase(room) != 0:
        return soap_responses["wrong_phase"]
    room.attributes["soap_applied"] = True
    return soap_responses["applied"]
