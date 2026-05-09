"""Room-entry routing and side-effect helpers for movement commands.

Each puzzle junction has an entry handler that fires once when the player
arrives.  Handlers roll puzzle outcomes, wire exit destinations dynamically,
or mutate game-state flags.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

from game.engine import GameEngine
from game.state import GameState

RoomEntryHandler = Callable[[GameEngine, GameState], None]
"""Callable type for functions invoked when the player enters a specific room."""

_ClueRoutedRoomSpec = tuple[
    str,
    str,
    str,
    str,
    str | None,
    str | None,
    Callable[[GameState], None] | None,
]
"""Tuple spec for wiring one clue-routed room entry handler.

Fields: ``room_id``, ``clue_key``, ``correct_destination``,
``wrong_destination``, ``wrong_way_return_room_id``, ``rolled_flag``,
and ``roll_handler``.
"""


def _route(exits: dict[str, str | None], correct: str, yes: str, no: str) -> None:
    """Wire forward/left/right exits so only one direction leads to the target.

    Parameters
    ----------
    exits : dict[str, str]
        The ``room.exits`` dict to mutate in place.
    correct : str
        The correct direction (``"forward"``, ``"left"``, or ``"right"``).
    yes : str
        Destination ``room_id`` for the correct direction.
    no : str
        Destination ``room_id`` for all other cardinal directions.
    """
    for direction in ("forward", "left", "right"):
        exits[direction] = yes if direction == correct else no


def _wire_flavor_chain(
    engine: GameEngine, chain: list[str], return_room_id: str
) -> None:
    """Wire each flavor room's forward exit into the next room in the chain.

    The last flavor room's forward exit loops back to *return_room_id*
    so the player returns to the puzzle junction after the detour.

    Parameters
    ----------
    engine : GameEngine
        Live engine whose ``rooms`` dict is mutated.
    chain : list[str]
        Ordered list of flavor room IDs forming the wrong-way detour.
    return_room_id : str
        Room to return to after the last flavor room.
    """
    for room_id, next_id in zip(chain, chain[1:] + [return_room_id]):
        engine.rooms[room_id].exits["forward"] = next_id


def _roll_once(
    state: GameState, rolled_flag: str, roll_handler: Callable[[GameState], None]
) -> None:
    """Invoke a puzzle roll handler exactly once per playthrough.

    Parameters
    ----------
    state : GameState
        Mutable game state; ``rolled_flag`` is set after the first roll.
    rolled_flag : str
        Flag name used to guard against re-rolling.
    roll_handler : Callable[[GameState], None]
        The puzzle roll function to call on first entry.
    """
    if state.has_flag(rolled_flag):
        return
    roll_handler(state)
    state.set_flag(rolled_flag)


def _enter_clue_routed_room(
    engine: GameEngine,
    state: GameState,
    *,
    room_id: str,
    clue_key: str,
    correct_destination: str,
    wrong_destination: str,
    wrong_way_return_room_id: str | None = None,
    rolled_flag: str | None = None,
    roll_handler: Callable[[GameState], None] | None = None,
) -> None:
    """Optionally roll a clue once, then wire the exit table for one puzzle room.

    Parameters
    ----------
    engine : GameEngine
        Live engine.
    state : GameState
        Mutable game state.
    room_id : str
        Room whose exits are wired.
    clue_key : str
        Key in ``state.active_clues`` that holds the correct direction.
    correct_destination : str
        Room ID reached when the player chooses the right direction.
    wrong_destination : str
        Room ID reached when the player chooses any other direction.
    wrong_way_return_room_id : str or None, optional
        When given, the wrong-destination room’s forward exit is wired back
        here so the player is funnelled back to retry.
    rolled_flag : str or None, optional
        Together with *roll_handler*, controls one-time puzzle initialisation.
    roll_handler : Callable[[GameState], None] or None, optional
        Roll function invoked via :func:`_roll_once` on first entry.
    """
    if rolled_flag is not None and roll_handler is not None:
        _roll_once(state, rolled_flag, roll_handler)
    correct_dir = state.active_clues.get(clue_key, "")
    _route(
        engine.rooms[room_id].exits,
        correct_dir,
        correct_destination,
        wrong_destination,
    )
    if wrong_way_return_room_id is not None:
        engine.rooms[wrong_destination].exits["forward"] = wrong_way_return_room_id


def build_room_entry_handlers(
    *,
    step1_roll_handler: Callable[[GameState], None],
    step2_roll_handler: Callable[[GameState], None],
    step3_roll_handler: Callable[[GameState], None],
    pick_flavor_count: Callable[[], int],
    sample_flavor_rooms: Callable[[int], list[str]],
) -> dict[str, RoomEntryHandler]:
    """Build the destination-to-handler table for all puzzle room entries.

    Parameters
    ----------
    step1_roll_handler : Callable[[GameState], None]
        Initialises Step 1 clues when ``intersection_4way`` is first entered.
    step2_roll_handler : Callable[[GameState], None]
        Initialises Step 2 clues when ``bathroom`` is first entered.
    step3_roll_handler : Callable[[GameState], None]
        Initialises Step 3 clues when ``hallway_janitor`` is first entered.
    pick_flavor_count : Callable[[], int]
        Returns a random number of flavor rooms for the wrong-way detour chain.
    sample_flavor_rooms : Callable[[int], list[str]]
        Returns a random sample of flavor room IDs of the given length.

    Returns
    -------
    dict[str, RoomEntryHandler]
        Maps ``room_id`` strings to their entry handler callables.
    """

    def enter_intersection_4way(engine: GameEngine, state: GameState) -> None:
        """Roll Step 1, wire the flavor detour chain, and set the junction exits."""
        step1_roll_handler(state)
        correct_dir = state.active_clues["step1_correct_dir"]
        chain = sample_flavor_rooms(pick_flavor_count())
        _wire_flavor_chain(engine, chain, "intersection_4way")
        _route(
            engine.rooms["intersection_4way"].exits,
            correct_dir,
            "intersection_3way",
            chain[0],
        )

    def enter_bathroom(engine: GameEngine, state: GameState) -> None:
        """Seed Step 2 puzzle state the first time the player enters the bathroom."""
        _roll_once(state, "step2_rolled", step2_roll_handler)
        engine.rooms["bathroom"].attributes["sink_running"] = True

    def enter_room_314(_engine: GameEngine, state: GameState) -> None:
        """Set game_over + won when the player reaches Room 314."""
        state.won = True
        state.game_over = True

    clue_routed_specs: tuple[_ClueRoutedRoomSpec, ...] = (
        (
            "intersection_3way_exit",
            "step2_mirror_dir",
            "hallway_janitor",
            "flavor_copy_room",
            None,
            None,
            None,
        ),
        (
            "hallway_janitor",
            "step3_correct_dir",
            "hallway_final",
            "flavor_copy_room",
            "hallway_janitor",
            "step3_rolled",
            step3_roll_handler,
        ),
    )

    clue_routed_handlers: dict[str, RoomEntryHandler] = {
        room_id: partial(
            _enter_clue_routed_room,
            room_id=room_id,
            clue_key=clue_key,
            correct_destination=correct_destination,
            wrong_destination=wrong_destination,
            wrong_way_return_room_id=wrong_way_return_room_id,
            rolled_flag=rolled_flag,
            roll_handler=roll_handler,
        )
        for (
            room_id,
            clue_key,
            correct_destination,
            wrong_destination,
            wrong_way_return_room_id,
            rolled_flag,
            roll_handler,
        ) in clue_routed_specs
    }

    return {
        "intersection_4way": enter_intersection_4way,
        "bathroom": enter_bathroom,
        **clue_routed_handlers,
        "room_314": enter_room_314,
    }


def handle_room_entry(
    room_entry_handlers: dict[str, RoomEntryHandler],
    engine: GameEngine,
    state: GameState,
    destination_id: str,
) -> None:
    """Fire any registered entry handler for *destination_id*.

    Parameters
    ----------
    room_entry_handlers : dict[str, RoomEntryHandler]
        Handler table from :func:`build_room_entry_handlers`.
    engine : GameEngine
        Live engine.
    state : GameState
        Mutable game state.
    destination_id : str
        Room ID the player just entered.
    """
    handler = room_entry_handlers.get(destination_id)
    if handler is not None:
        handler(engine, state)
