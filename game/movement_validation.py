"""Movement validation helpers and shared movement rule tables.

Defines :data:`PuzzleDirectionRule`, the rule tuple structure checked on
every directional move, and the top-level helpers that apply those rules.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from game.engine import GameEngine
from game.room import Room
from game.state import GameState

PuzzleDirectionRule = tuple[
    str,
    tuple[str, ...] | None,
    Callable[[str, GameState], bool],
    str,
    int,
    str,
    str | None,
]
"""A 7-tuple describing one puzzle direction gate.

Fields (positional):

0. ``active_room_id`` (*str*) — room where the rule is active.
1. ``allowed_verbs`` (*tuple[str, ...] or None*) — directions the rule
   checks; ``None`` means all directions.
2. ``is_correct_direction`` (*Callable[[str, GameState], bool]*) —
   returns ``True`` when the player chose the correct direction.
3. ``wrong_message_key`` (*str*) — key in the ``move_responses`` dict
   for the wrong-way feedback string.
4. ``solved_step`` (*int*) — ``state.puzzle_step`` value when solved.
5. ``solved_flag`` (*str*) — flag set on ``state`` when solved.
6. ``wrong_turn_flag`` (*str or None*) — optional flag set on wrong turns.
"""
WrongWayHandler = Callable[
    [GameEngine, GameState, str, str, str | None],
    str,
]
"""Callable type for wrong-way move handlers.

Signature: ``(engine, state, destination_id, message_key, wrong_turn_flag) -> str``.
"""

SPECIAL_MOVE_DESTINATIONS: dict[str, str] = {
    "__lobby_forward_blocked__": "lobby_forward_blocked",
    "__lobby_back_blocked__": "lobby_back_blocked",
}


def build_puzzle_move_rules(
    step1_direction_check: Callable[[str, GameState], bool],
    step3_direction_check: Callable[[str, GameState], bool],
) -> tuple[PuzzleDirectionRule, ...]:
    """Return the tuple of direction-gated puzzle movement rules.

    Parameters
    ----------
    step1_direction_check : Callable[[str, GameState], bool]
        Returns ``True`` when the player's verb matches the Step 1 clue.
    step3_direction_check : Callable[[str, GameState], bool]
        Returns ``True`` when the player's verb matches the Step 3 clue.

    Returns
    -------
    tuple[PuzzleDirectionRule, ...]
        Ordered rules applied left-to-right in :func:`puzzle_move_response`.
    """
    return (
        (
            "intersection_4way",
            None,
            step1_direction_check,
            "wrong_4way",
            1,
            "step1_solved",
            "step1_wrong_way",
        ),
        (
            "hallway_janitor",
            ("forward", "left", "right"),
            step3_direction_check,
            "wrong_janitor",
            3,
            "step3_solved",
            None,
        ),
    )


def _validate_direction_puzzle_move(
    rule: PuzzleDirectionRule,
    wrong_way_handler: WrongWayHandler,
    engine: GameEngine,
    room: Room,
    verb: str,
    state: GameState,
    destination_id: str,
) -> str | None:
    """Apply one :data:`PuzzleDirectionRule` to the current move.

    Returns ``None`` when the rule is inactive (wrong room, verb not in
    ``allowed_verbs``) or when the player chose the correct direction
    (state is advanced but ``None`` is still returned so the move
    proceeds normally).  Returns a non-empty response string only when
    the player went the wrong way.

    Parameters
    ----------
    rule : PuzzleDirectionRule
        The rule tuple to evaluate.
    wrong_way_handler : WrongWayHandler
        Callback that commits the wrong-way move and returns a response.
    engine : GameEngine
        Live engine.
    room : Room
        Current room.
    verb : str
        Direction verb chosen by the player.
    state : GameState
        Mutable game state.
    destination_id : str
        Exit destination resolved from the room's exit table.

    Returns
    -------
    str or None
        Wrong-way response string, or ``None`` to allow normal move.
    """
    (
        active_room_id,
        allowed_verbs,
        is_correct_direction,
        wrong_message_key,
        solved_step,
        solved_flag,
        wrong_turn_flag,
    ) = rule
    if room.room_id != active_room_id:
        return None
    if allowed_verbs is not None and verb not in allowed_verbs:
        return None
    if not is_correct_direction(verb, state):
        return wrong_way_handler(
            engine,
            state,
            destination_id,
            wrong_message_key,
            wrong_turn_flag,
        )
    state.puzzle_step = solved_step
    state.set_flag(solved_flag, True)
    return None


def puzzle_move_response(
    rules: Sequence[PuzzleDirectionRule],
    wrong_way_handler: WrongWayHandler,
    engine: GameEngine,
    room: Room,
    verb: str,
    state: GameState,
    destination_id: str,
) -> str | None:
    """Check all puzzle direction rules and return a wrong-way response if any fires.

    Parameters
    ----------
    rules : Sequence[PuzzleDirectionRule]
        Ordered rule tuples to evaluate.
    wrong_way_handler : WrongWayHandler
        Callback for committing wrong-way moves.
    engine : GameEngine
        Live engine.
    room : Room
        Current room.
    verb : str
        Direction verb chosen by the player.
    state : GameState
        Mutable game state.
    destination_id : str
        Exit destination resolved from the room's exits.

    Returns
    -------
    str or None
        First non-``None`` wrong-way response, or ``None`` when all rules pass.
    """
    for rule in rules:
        puzzle_result = _validate_direction_puzzle_move(
            rule,
            wrong_way_handler,
            engine,
            room,
            verb,
            state,
            destination_id,
        )
        if puzzle_result is not None:
            return puzzle_result
    return None


def special_move_response(
    destination_id: str | None, move_responses: Mapping[str, str]
) -> str | None:
    """Return a canned response for a sentinel destination, or ``None`` for real rooms.

    Sentinel destinations are keys in :data:`SPECIAL_MOVE_DESTINATIONS`
    (e.g. ``"__lobby_forward_blocked__"``) that map to a response key
    instead of a real room ID.

    Parameters
    ----------
    destination_id : str or None
        Exit value from the room's exits dict.
    move_responses : Mapping[str, str]
        Movement response strings from ``commands.yaml``.

    Returns
    -------
    str or None
        The canned response string, or ``None`` when no sentinel matched.
    """
    if destination_id is None:
        return move_responses["blocked"]
    response_key = SPECIAL_MOVE_DESTINATIONS.get(destination_id)
    if response_key is None:
        return None
    return move_responses[response_key]
