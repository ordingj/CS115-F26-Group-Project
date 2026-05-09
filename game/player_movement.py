"""Movement command registration and puzzle room-entry helpers.

Exports :func:`register_movement_commands`, which wires the four directional
verbs (``forward``, ``back``, ``left``, ``right``) to the full movement
pipeline: validation → bathroom block check → puzzle routing → commit +
arrival hooks.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping
from functools import partial

from game.bathroom import bathroom_exit_block_message
from game.command import CommandRegistry
from game.engine import GameEngine
from game.movement_routing import build_room_entry_handlers, handle_room_entry
from game.movement_validation import (
    build_puzzle_move_rules,
    puzzle_move_response,
    special_move_response,
)
from game.puzzle import (
    step1_is_correct,
    step1_roll,
    step2_roll,
    step3_is_correct,
    step3_roll,
)
from game.state import GameState
from game.world import FLAVOR_ROOM_POOL


def register_movement_commands(
    registry: CommandRegistry,
    engine_ref: list[GameEngine | None],
    move_responses: Mapping[str, str],
) -> None:
    """Register movement verbs and their puzzle-specific room-entry flow.

    Parameters
    ----------
    registry : CommandRegistry
        The registry to populate with ``forward``, ``back``, ``left``,
        and ``right`` verbs.
    engine_ref : list[GameEngine or None]
        Mutable cell holding the live engine (same pattern as
        :func:`~game.player_commands.build_commands`).
    move_responses : Mapping[str, str]
        Movement response strings from ``commands.yaml``.
    """

    def _commit_move(
        engine: GameEngine,
        destination_id: str,
        state: GameState,
        on_arrival: Callable[[], None] | None = None,
    ) -> None:
        """Commit a room change, run any arrival hook, and re-render the destination.

        Parameters
        ----------
        engine : GameEngine
            Live engine for signalling transitions and re-rendering.
        destination_id : str
            ``room_id`` of the room to enter.
        state : GameState
            Mutable game state; ``current_room_id`` is updated in place.
        on_arrival : Callable[[], None] or None, optional
            Optional hook invoked after the room change but before rendering
            (used for puzzle roll-ins and flavor-chain wiring).
        """
        state.current_room_id = destination_id
        if on_arrival is not None:
            on_arrival()
        engine.signal_transition()
        engine.describe_current_room()

    def _bounce_wrong_way(
        engine: GameEngine,
        state: GameState,
        destination_id: str,
        message_key: str,
        wrong_turn_flag: str | None = None,
    ) -> str:
        """Commit a wrong-way move and return the matching penalty response.

        Parameters
        ----------
        engine : GameEngine
            Live engine.
        state : GameState
            Mutable game state; ``wrong_turns`` is incremented.
        destination_id : str
            Room to teleport the player into (even though it’s wrong).
        message_key : str
            Key in *move_responses* for the wrong-way feedback string.
        wrong_turn_flag : str or None, optional
            If provided, also sets a named flag on *state*.

        Returns
        -------
        str
            The wrong-way response text.
        """
        state.wrong_turns += 1
        if wrong_turn_flag is not None:
            state.set_flag(wrong_turn_flag, True)
        _commit_move(engine, destination_id, state)
        return move_responses[message_key]

    room_entry_handlers = build_room_entry_handlers(
        step1_roll_handler=lambda state: step1_roll(state),
        step2_roll_handler=lambda state: step2_roll(state),
        step3_roll_handler=lambda state: step3_roll(state),
        pick_flavor_count=lambda: random.randint(2, 3),
        sample_flavor_rooms=lambda count: random.sample(FLAVOR_ROOM_POOL, count),
    )

    puzzle_move_rules = build_puzzle_move_rules(step1_is_correct, step3_is_correct)

    def handle_move(verb: str, target: str | None, state: GameState) -> str:
        """Move the player one step in the *verb* direction.

        Full pipeline:

        1. Verify exit exists in the current room.
        2. Check for special sentinel destinations (e.g. ``__blocked__``).
        3. Check bathroom exit block (Step 2 soap hands).
        4. Check puzzle routing rules (Step 1 / Step 3 direction validation).
        5. Commit the move and run arrival hooks.

        Parameters
        ----------
        verb : str
            Direction word: ``"forward"``, ``"back"``, ``"left"``,
            or ``"right"``.
        target : str or None
            Unused; movement verbs don’t take targets.
        state : GameState
            Mutable game state.

        Returns
        -------
        str
            Response text (empty string when a describe call handles output).
        """
        engine = engine_ref[0]
        if engine is None:
            return "Error: engine not initialised."
        room = engine.current_room()
        if room is None:
            return "You are nowhere."
        if verb not in room.exits:
            return move_responses["no_exit"]
        destination_id = room.exits[verb]
        canned_move_response = special_move_response(destination_id, move_responses)
        if canned_move_response is not None:
            return canned_move_response

        blocked_message = bathroom_exit_block_message(room, state, move_responses)
        if blocked_message is not None:
            return blocked_message

        puzzle_result = puzzle_move_response(
            puzzle_move_rules,
            _bounce_wrong_way,
            engine,
            room,
            verb,
            state,
            destination_id,
        )
        if puzzle_result is not None:
            return puzzle_result

        _commit_move(
            engine,
            destination_id,
            state,
            partial(
                handle_room_entry, room_entry_handlers, engine, state, destination_id
            ),
        )
        return ""

    for verb in ("forward", "back", "left", "right"):
        registry.register(verb, handle_move)
