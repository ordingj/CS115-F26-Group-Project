"""Player command registration and puzzle-specific command handlers.

All game verbs are registered here.  Puzzle-specific verbs (RINSE, STOP,
SOAP, LISTEN, LOOK at targets, READ) are handled by closures that capture
``engine_ref`` to reach the live engine at call time without a circular
import.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import partial

from game import load_yaml_data
from game.bathroom import (
    apply_soap,
    bathroom_mirror_text,
    bathroom_sink_text,
    rinse_hands,
    stop_sink,
)
from game.basic_commands import register_basic_commands
from game.command import (
    CommandRegistry,
    TargetStateHandler,
    register_target_state_handler,
)
from game.engine import GameEngine
from game.janitor import janitor_listen_text
from game.player_movement import register_movement_commands
from game.room import Room
from game.state import GameState

_CMD: dict = load_yaml_data("commands.yaml")["responses"]

_RoomTargetHandler = Callable[[Room, GameState], str]

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

    def _register_room_action(
        room_id: str,
        missing_response: str,
        action: Callable[[Room, GameState], str],
        *verbs: str,
    ) -> None:
        """Register one room-gated action under one or more command verbs."""

        def handle_room_action(_target: str | None, state: GameState) -> str:
            """Run *action* only when the player is currently in *room_id*."""
            room = _current_room()
            if room is None or room.room_id != room_id:
                return missing_response
            return action(room, state)

        register_target_state_handler(
            registry,
            handle_room_action,
            *verbs,
        )

    def _register_room_target_command(
        handlers: Mapping[tuple[str, str], _RoomTargetHandler],
        fallback: TargetStateHandler,
        *verbs: str,
    ) -> None:
        """Register a verb that checks room-target handlers before falling back."""

        def handle_room_target(target: str | None, state: GameState) -> str:
            """Try a room-specific target handler first; fall back to the generic fallback handler."""
            room = _current_room()
            if room is not None and target is not None:
                handler = handlers.get((room.room_id, target))
                if handler is not None:
                    return handler(room, state)
            return fallback(target, state)

        register_target_state_handler(registry, handle_room_target, *verbs)

    register_movement_commands(registry, engine_ref, _CMD["move"])

    def handle_detour_sign(_room: Room, _state: GameState) -> str:
        """Return the fixed detour sign text for both supported lobby sign aliases."""
        return _CMD["read"]["detour_sign"]

    def handle_bathroom_look_mirror(_room: Room, state: GameState) -> str:
        """Return the mirror text, keeping the fogged response until hands are clean."""
        return bathroom_mirror_text(state, _CMD["look"]["mirror_fogged"])

    def handle_bathroom_look_sink(room: Room, state: GameState) -> str:
        """Return the sink description based on current wash phase and running state."""
        return bathroom_sink_text(room, state, _CMD["look"])

    def handle_bathroom_read_mirror(_room: Room, state: GameState) -> str:
        """Return the readable mirror text, keeping the fogged response until Step 2 is solved."""
        return bathroom_mirror_text(state, _CMD["read"]["mirror_fogged"])

    look_target_handlers: dict[tuple[str, str], _RoomTargetHandler] = {
        ("bathroom", "mirror"): handle_bathroom_look_mirror,
        ("bathroom", "sink"): handle_bathroom_look_sink,
    }

    read_target_handlers: dict[tuple[str, str], _RoomTargetHandler] = {
        ("lobby", "sign"): handle_detour_sign,
        ("lobby", "detour_sign"): handle_detour_sign,
        ("bathroom", "mirror"): handle_bathroom_read_mirror,
    }

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

    _register_room_target_command(
        look_target_handlers, _look_fallback, "look", "examine"
    )

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

    _register_room_target_command(read_target_handlers, _read_fallback, "read")

    _register_room_action(
        "bathroom",
        _CMD["rinse"]["no_location"],
        partial(rinse_hands, rinse_responses=_CMD["rinse"]),
        "rinse",
        "wash",
    )
    _register_room_action(
        "bathroom",
        _CMD["stop"]["no_location"],
        partial(stop_sink, stop_responses=_CMD["stop"]),
        "stop",
    )

    def _listen_in_janitor_hallway(room: Room, state: GameState) -> str:
        """Return the janitor chorus and mark the song as heard when available."""
        heard_text = janitor_listen_text(state, _CMD["listen"]["janitor_prefix"])
        if not heard_text:
            return _CMD["listen"]["silence"]
        room.attributes["song_heard"] = True
        state.set_flag("step3_song_heard")
        return heard_text

    _register_room_action(
        "hallway_janitor",
        _CMD["listen"]["silence"],
        _listen_in_janitor_hallway,
        "listen",
    )

    _register_room_action(
        "bathroom",
        _CMD["soap"]["no_location"],
        partial(apply_soap, soap_responses=_CMD["soap"]),
        "soap",
    )

    register_basic_commands(registry, _CMD)

    return registry
