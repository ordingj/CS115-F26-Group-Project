"""Player command registration and puzzle-specific command handlers.

All game verbs are registered here. Puzzle-specific verbs (RINSE, STOP,
SOAP, LISTEN, LOOK at targets, READ) still capture ``engine_ref`` to reach
the live engine at call time without a circular import, but the room-aware
registry adapters now live in :mod:`game.command` instead of this module,
and the bathroom/janitor-specific command spec fragments live with their
owning modules.
"""

from __future__ import annotations

from game import load_yaml_data
from game.puzzles.bathroom import bathroom_room_state_commands
from game.puzzles.bathroom_view import (
    bathroom_look_target_handlers,
    bathroom_read_target_handlers,
)
from game.commands.basic_commands import register_basic_commands
from game.commands.command import (
    CommandRegistry,
    RoomStateCommandSpec,
    RoomTargetCommandSpec,
    fixed_room_state_handler,
    register_room_state_command_specs,
    register_room_target_command_specs,
)
from game.engine.engine import GameEngine
from game.puzzles.intersection import intersection_read_target_handlers
from game.puzzles.janitor import janitor_room_state_commands
from game.commands.player_movement import register_movement_commands
from game.room import Room
from game.state import GameState

_CMD: dict = load_yaml_data("commands.yaml")["responses"]

_ITEM_ALIASES: dict[str, str] = {
    "backpack": "backpack",
    "bag": "backpack",
    "phone": "phone",
    "cell": "phone",
    "mobile": "phone",
    "keys": "keys",
    "key": "keys",
    "wallet": "wallet",
    "watch": "watch",
}


def build_commands(engine_ref: list[GameEngine | None]) -> CommandRegistry:
    """Register all player-facing commands and return the populated registry.

    ``engine_ref`` is a one-element list used as a mutable cell so that
    command handlers can access the live engine instance without creating
    a circular import.  The list is populated by the caller *after* this
    function returns.

    Parameters
    ----------
    engine_ref : list[GameEngine or None]
        A ``[None]`` list; ``engine_ref[0]`` will be the live
        :class:`~game.engine.GameEngine` by the time any handler is invoked.

    Returns
    -------
    CommandRegistry
        A :class:`~game.command.CommandRegistry` with every verb registered.
    """
    registry = CommandRegistry(_CMD["unknown"])

    def _live_engine() -> GameEngine | None:
        """Return the live engine instance stored in the *engine_ref* cell."""
        return engine_ref[0]

    def _current_room() -> Room | None:
        """Return the player's current room, or ``None`` if the engine is unavailable."""
        engine = _live_engine()
        return engine.current_room() if engine else None

    register_movement_commands(registry, engine_ref, _CMD["move"])

    def _look_fallback(target: str | None, state: GameState) -> str:
        """Describe the room or one inventory item when no room-target handler applies."""
        engine = _live_engine()
        if engine is None:
            return ""
        item_key = _ITEM_ALIASES.get(target or "")
        if item_key and item_key in state.inventory:
            value = _CMD["inventory"][item_key]
            return (
                value.format(time=state.formatted_time())
                if item_key == "watch"
                else value
            )
        engine.describe_current_room()
        return ""

    def _read_fallback(target: str | None, state: GameState) -> str:
        """Read a named room item when no room-target handler applies."""
        if target is None:
            return _CMD["read"]["no_target"]
        room = _current_room()
        if room is None:
            return _CMD["read"]["not_here"].format(target=target)
        if target in room.items:
            return _CMD["read"]["generic"].format(item=room.items[target])
        return _CMD["read"]["not_here"].format(target=target)

    detour_sign_handler = fixed_room_state_handler(_CMD["read"]["detour_sign"])
    bathroom_look_handlers = bathroom_look_target_handlers(_CMD)
    bathroom_read_handlers = bathroom_read_target_handlers(_CMD)
    intersection_read_handlers = intersection_read_target_handlers(_CMD)

    room_target_commands: tuple[RoomTargetCommandSpec, ...] = (
        (
            ("look", "examine"),
            bathroom_look_handlers,
            _look_fallback,
        ),
        (
            ("read",),
            {
                ("lobby", "sign"): detour_sign_handler,
                ("lobby", "detour_sign"): detour_sign_handler,
                **intersection_read_handlers,
                **bathroom_read_handlers,
            },
            _read_fallback,
        ),
    )

    register_room_target_command_specs(registry, _current_room, room_target_commands)

    room_state_commands: tuple[RoomStateCommandSpec, ...] = (
        *bathroom_room_state_commands(_CMD),
        *janitor_room_state_commands(_CMD),
    )

    register_room_state_command_specs(registry, _current_room, room_state_commands)

    register_basic_commands(registry, _CMD)

    return registry
