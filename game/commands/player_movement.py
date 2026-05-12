"""Movement command registration plus movement-specific puzzle helpers.

This module owns the full directional movement pipeline: special blocker
responses, direction-gated puzzle validation, wrong-way detours, and room
entry side effects for puzzle rooms.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import partial

from game.puzzles.bathroom import bathroom_exit_block_message, step2_roll
from game.commands.command import CommandRegistry
from game.engine.engine import GameEngine
from game.puzzles.intersection import step1_roll
from game.puzzles.janitor import step3_roll
from game.puzzles.puzzle import (
    clue_direction_matches,
)
from game.room import Room
from game.state import GameState
from game.world import FLAVOR_ROOM_POOL


@dataclass(frozen=True)
class PuzzleDirectionRule:
    """Named config for one direction-gated puzzle move rule."""

    active_room_id: str
    allowed_verbs: tuple[str, ...] | None
    clue_key: str
    wrong_message_key: str
    solved_step: int
    solved_flag: str
    wrong_turn_flag: str | None = None


WrongWayHandler = Callable[
    [GameEngine, GameState, str, str, str | None],
    str,
]
"""Callable type for wrong-way move handlers."""

RoomEntryHandler = Callable[[GameEngine, GameState], None]
"""Callable type for room-entry side-effect handlers."""


@dataclass(frozen=True)
class _ConfiguredRoomEntrySpec:
    """Declarative spec for one room-entry handler built from shared setup steps."""

    room_id: str
    clue_key: str | None = None
    correct_destination: str | None = None
    wrong_destination: str | None = None
    wrong_way_return_room_id: str | None = None
    rolled_flag: str | None = None
    roll_handler: Callable[[GameState], None] | None = None
    room_attribute_updates: Mapping[str, object] = field(default_factory=dict)


SPECIAL_MOVE_DESTINATIONS: dict[str, str] = {
    "__lobby_forward_blocked__": "lobby_forward_blocked",
    "__lobby_back_blocked__": "lobby_back_blocked",
}


PUZZLE_MOVE_RULES: tuple[PuzzleDirectionRule, ...] = (
    PuzzleDirectionRule(
        active_room_id="intersection_4way",
        allowed_verbs=None,
        clue_key="step1_correct_dir",
        wrong_message_key="wrong_4way",
        solved_step=1,
        solved_flag="step1_solved",
        wrong_turn_flag="step1_wrong_way",
    ),
    PuzzleDirectionRule(
        active_room_id="hallway_janitor",
        allowed_verbs=("forward", "left", "right"),
        clue_key="step3_correct_dir",
        wrong_message_key="wrong_janitor",
        solved_step=3,
        solved_flag="step3_solved",
    ),
)
"""Direction-gated puzzle movement rules keyed by the active clue to validate."""


def _run_step1_roll(state: GameState) -> None:
    """Late-bind Step 1 clue seeding so tests can still patch ``step1_roll``."""
    step1_roll(state)


def _run_step2_roll(state: GameState) -> None:
    """Late-bind Step 2 clue seeding so tests can still patch ``step2_roll``."""
    step2_roll(state)


def _run_step3_roll(state: GameState) -> None:
    """Late-bind Step 3 clue seeding so tests can still patch ``step3_roll``."""
    step3_roll(state)


def _pick_flavor_count() -> int:
    """Return the randomized flavor-chain length for a wrong-way detour."""
    return random.randint(2, 3)


def _pick_hallway_detour_count() -> int:
    """Return the randomized detour length for one short interstitial chain."""
    return random.randint(1, 3)


def _sample_flavor_rooms(
    state: GameState,
    count: int,
    excluded_room_ids: set[str] | None = None,
) -> list[str]:
    """Return one detour chain, preferring unused interstitial rooms first."""
    excluded = excluded_room_ids or set()
    selected: list[str] = []

    while len(selected) < count:
        unused_pool = [
            room_id
            for room_id in FLAVOR_ROOM_POOL
            if room_id not in excluded
            and room_id not in state.used_interstitial_room_ids
            and room_id not in selected
        ]
        if unused_pool:
            draw_count = min(count - len(selected), len(unused_pool))
            chosen = random.sample(unused_pool, draw_count)
            selected.extend(chosen)
            state.used_interstitial_room_ids.update(chosen)
            continue

        recycle_pool = [
            room_id
            for room_id in FLAVOR_ROOM_POOL
            if room_id not in excluded and room_id not in selected
        ]
        chosen = random.sample(recycle_pool, count - len(selected))
        selected.extend(chosen)
        state.used_interstitial_room_ids.update(chosen)

    return selected


def _validate_direction_puzzle_move(
    rule: PuzzleDirectionRule,
    wrong_way_handler: WrongWayHandler,
    engine: GameEngine,
    room: Room,
    verb: str,
    state: GameState,
    destination_id: str,
) -> str | None:
    """Apply one puzzle direction rule to the current move."""
    if room.room_id != rule.active_room_id:
        return None
    if rule.allowed_verbs is not None and verb not in rule.allowed_verbs:
        return None
    if not clue_direction_matches(verb, state, rule.clue_key):
        return wrong_way_handler(
            engine,
            state,
            destination_id,
            rule.wrong_message_key,
            rule.wrong_turn_flag,
        )
    state.puzzle_step = rule.solved_step
    state.set_flag(rule.solved_flag, True)
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
    """Return the first wrong-way response triggered by the puzzle rules."""
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


def _route(exits: dict[str, str | None], correct: str, yes: str, no: str) -> None:
    """Wire forward/left/right exits so only *correct* reaches *yes*."""
    for direction in ("forward", "left", "right"):
        exits[direction] = yes if direction == correct else no


def _wire_flavor_chain(
    engine: GameEngine, chain: list[str], return_room_id: str
) -> None:
    """Wire each sampled flavor room toward the next detour room.

    Interstitial flavor rooms always expose both ``forward`` and ``back`` so
    either direction keeps the player moving through the detour chain until
    they hit the configured return room.
    """
    for room_id, next_id in zip(chain, chain[1:] + [return_room_id]):
        engine.rooms[room_id].exits["forward"] = next_id
        engine.rooms[room_id].exits["back"] = next_id


def _roll_once(
    state: GameState, rolled_flag: str, roll_handler: Callable[[GameState], None]
) -> None:
    """Invoke a puzzle roll handler only on the first matching entry."""
    if state.has_flag(rolled_flag):
        return
    roll_handler(state)
    state.set_flag(rolled_flag)


def _enter_configured_room(
    engine: GameEngine,
    state: GameState,
    *,
    spec: _ConfiguredRoomEntrySpec,
) -> None:
    """Apply the shared setup flow for bathroom and clue-routed room entries."""
    if spec.rolled_flag is not None and spec.roll_handler is not None:
        _roll_once(state, spec.rolled_flag, spec.roll_handler)
    if spec.room_attribute_updates:
        engine.rooms[spec.room_id].attributes.update(spec.room_attribute_updates)
    if (
        spec.clue_key is None
        or spec.correct_destination is None
        or spec.wrong_destination is None
    ):
        return
    correct_dir = state.active_clues.get(spec.clue_key, "")
    _route(
        engine.rooms[spec.room_id].exits,
        correct_dir,
        spec.correct_destination,
        spec.wrong_destination,
    )
    if spec.wrong_way_return_room_id is not None:
        _wire_flavor_chain(
            engine,
            [spec.wrong_destination],
            spec.wrong_way_return_room_id,
        )


def build_room_entry_handlers(
    *,
    step1_roll_handler: Callable[[GameState], None],
    step2_roll_handler: Callable[[GameState], None],
    step3_roll_handler: Callable[[GameState], None],
    pick_hallway_detour_count: Callable[[], int],
    pick_flavor_count: Callable[[], int],
    sample_flavor_rooms: Callable[[GameState, int, set[str] | None], list[str]],
) -> dict[str, RoomEntryHandler]:
    """Build the destination-to-handler table for puzzle room entry effects."""

    def enter_hallway_approach(engine: GameEngine, state: GameState) -> None:
        """Wire both hallway directions into a short randomized detour toward the 4-way."""
        chain = sample_flavor_rooms(state, pick_hallway_detour_count(), None)
        _wire_flavor_chain(engine, chain, "intersection_4way")
        hallway_exits = engine.rooms["hallway_approach"].exits
        hallway_exits["forward"] = chain[0]
        hallway_exits["back"] = chain[0]

    def enter_intersection_4way(engine: GameEngine, state: GameState) -> None:
        """Roll Step 1 and wire both the correct and wrong routes out of the 4-way."""
        returning_to_intersection = state.has_flag("step1_seen_intersection")
        state.set_flag("step1_seen_intersection")
        if returning_to_intersection:
            state.set_flag("step1_returned_to_intersection")
        step1_roll_handler(state)
        correct_dir = state.active_clues["step1_correct_dir"]
        correct_chain = sample_flavor_rooms(
            state,
            pick_hallway_detour_count(),
            None,
        )
        wrong_chain = sample_flavor_rooms(
            state,
            pick_flavor_count(),
            set(correct_chain),
        )
        _wire_flavor_chain(engine, correct_chain, "intersection_3way")
        _wire_flavor_chain(engine, wrong_chain, "intersection_4way")
        _route(
            engine.rooms["intersection_4way"].exits,
            correct_dir,
            correct_chain[0],
            wrong_chain[0],
        )

    def enter_intersection_3way(engine: GameEngine, state: GameState) -> None:
        """Wire the visible side halls into a short detour that loops back to the junction."""
        chain = sample_flavor_rooms(state, pick_hallway_detour_count(), None)
        _wire_flavor_chain(engine, chain, "intersection_3way")
        junction_exits = engine.rooms["intersection_3way"].exits
        junction_exits["forward"] = "bathroom"
        junction_exits["back"] = "intersection_4way"
        junction_exits["left"] = chain[0]
        junction_exits["right"] = chain[0]

    def enter_intersection_3way_exit(engine: GameEngine, state: GameState) -> None:
        """Route the mirror-correct exit through a short detour before janitor."""
        chain = sample_flavor_rooms(
            state,
            pick_hallway_detour_count(),
            {"flavor_copy_room"},
        )
        _wire_flavor_chain(engine, chain, "hallway_janitor")
        _route(
            engine.rooms["intersection_3way_exit"].exits,
            state.active_clues.get("step2_mirror_dir", ""),
            chain[0],
            "flavor_copy_room",
        )
        _wire_flavor_chain(engine, ["flavor_copy_room"], "intersection_3way_exit")

    def enter_hallway_janitor(engine: GameEngine, state: GameState) -> None:
        """Route the song-correct exit through a short detour before the final stretch."""
        _roll_once(state, "step3_rolled", step3_roll_handler)
        chain = sample_flavor_rooms(
            state,
            pick_hallway_detour_count(),
            {"flavor_copy_room"},
        )
        _wire_flavor_chain(engine, chain, "hallway_final")
        _route(
            engine.rooms["hallway_janitor"].exits,
            state.active_clues.get("step3_correct_dir", ""),
            chain[0],
            "flavor_copy_room",
        )
        _wire_flavor_chain(engine, ["flavor_copy_room"], "hallway_janitor")

    def enter_room_314(_engine: GameEngine, state: GameState) -> None:
        """Mark the game as won when the player reaches Room 314."""
        state.won = True
        state.game_over = True

    configured_entry_specs: tuple[_ConfiguredRoomEntrySpec, ...] = (
        _ConfiguredRoomEntrySpec(
            room_id="bathroom",
            rolled_flag="step2_rolled",
            roll_handler=step2_roll_handler,
            room_attribute_updates={"sink_running": True},
        ),
    )

    configured_handlers: dict[str, RoomEntryHandler] = {
        spec.room_id: partial(
            _enter_configured_room,
            spec=spec,
        )
        for spec in configured_entry_specs
    }

    return {
        "hallway_approach": enter_hallway_approach,
        "intersection_4way": enter_intersection_4way,
        "intersection_3way": enter_intersection_3way,
        "intersection_3way_exit": enter_intersection_3way_exit,
        "hallway_janitor": enter_hallway_janitor,
        **configured_handlers,
        "room_314": enter_room_314,
    }


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
        on_arrival: RoomEntryHandler | None = None,
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
        on_arrival : RoomEntryHandler or None, optional
            Optional room-entry hook invoked after the room change but before
            rendering (used for puzzle roll-ins and flavor-chain wiring).
        """
        state.current_room_id = destination_id
        if on_arrival is not None:
            on_arrival(engine, state)
        if engine.should_render_arrival_room():
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
        step1_roll_handler=_run_step1_roll,
        step2_roll_handler=_run_step2_roll,
        step3_roll_handler=_run_step3_roll,
        pick_hallway_detour_count=_pick_hallway_detour_count,
        pick_flavor_count=_pick_flavor_count,
        sample_flavor_rooms=_sample_flavor_rooms,
    )

    puzzle_move_rules = PUZZLE_MOVE_RULES

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
            return move_responses["engine_not_initialised"]
        room = engine.current_room()
        if room is None:
            return move_responses["room_missing"]
        if verb not in room.exits:
            return move_responses["no_exit"]
        destination_id = room.exits[verb]
        if destination_id is None:
            return move_responses["blocked"]
        response_key = SPECIAL_MOVE_DESTINATIONS.get(destination_id)
        if response_key is not None:
            return move_responses[response_key]

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

        arrival_handler = room_entry_handlers.get(destination_id)
        _commit_move(
            engine,
            destination_id,
            state,
            arrival_handler,
        )
        return ""

    for verb in ("forward", "back", "left", "right"):
        registry.register(verb, handle_move)
