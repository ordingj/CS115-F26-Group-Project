"""Command asset type, parser, and dispatch registry.

Alongside the parser and registry, this module owns small registration
adapters that keep feature modules focused on command behavior instead of
repeating boilerplate to adapt handlers to the registry signature.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING

from game import load_yaml_data

if TYPE_CHECKING:
    from game.room import Room
    from game.state import GameState

# ── canonical verb sets ───────────────────────────────────────────────────────

MOVEMENT_VERBS: frozenset[str] = frozenset({"forward", "back", "left", "right"})
MOVEMENT_ALIASES: dict[str, str] = {
    "f": "forward",
    "b": "back",
    "l": "left",
    "r": "right",
}


def _canonicalize_movement_token(token: str) -> str:
    """Return the canonical movement verb for one direction token."""
    return MOVEMENT_ALIASES.get(token, token)


# Handler: (verb, target, state) -> message string shown to the player.
CommandHandler = Callable[[str, "str | None", "GameState"], str]
TargetStateHandler = Callable[["str | None", "GameState"], str]
StateOnlyHandler = Callable[["GameState"], str]
RoomStateHandler = Callable[["Room", "GameState"], str]
CurrentRoomProvider = Callable[[], "Room | None"]
TargetStateCommandSpec = tuple[tuple[str, ...], TargetStateHandler]
RoomTargetCommandSpec = tuple[
    tuple[str, ...],
    Mapping[tuple[str, str], RoomStateHandler],
    TargetStateHandler,
]
RoomStateCommandSpec = tuple[
    tuple[str, ...],
    str,
    str,
    RoomStateHandler,
]


@dataclass
class Command:
    """A parsed player command.

    Attributes
    ----------
    verb : str
        The action word (e.g. ``"forward"``, ``"read"``).
    target : str or None
        Optional object the action is directed at (e.g. ``"sign"``).
        ``None`` when the player typed only a verb with no target.
    """

    verb: str
    target: str | None = None  # e.g. "sign", "watch", "door"


class CommandParser:
    """Converts raw player input into a :class:`Command` object."""

    def parse(self, raw: str) -> Command:
        """Tokenise *raw* input and return a :class:`Command`.

        The first token becomes the verb (lower-cased); any remaining tokens
        are joined with spaces to form the target. Single-letter movement
        shortcuts are normalised to the canonical direction verbs, and
        ``go <direction>`` accepts the same shortcuts. An empty or
        whitespace-only string produces ``Command(verb="")``.

        Parameters
        ----------
        raw : str
            Raw player input string, typically from ``input()`` or the curses
            read loop.  Surrounding whitespace and mixed case are normalised.

        Returns
        -------
        Command
            Parsed command with the verb lower-cased and the optional target
            joined from all remaining tokens.
        """
        tokens = raw.strip().lower().split()
        if not tokens:
            # Empty input — return a no-op command so the caller can skip it
            # without a special-case check.
            return Command(verb="")
        verb = _canonicalize_movement_token(tokens[0])
        # Collapse all remaining tokens into one target string (e.g.
        # "read detour sign" → target="detour sign").
        target = " ".join(tokens[1:]) if len(tokens) > 1 else None
        # "go <direction>" is a common natural-language form.  Re-map it so
        # downstream handlers only need to handle bare direction verbs.
        if verb == "go" and target is not None:
            movement_target = _canonicalize_movement_token(target)
            if movement_target in MOVEMENT_VERBS:
                return Command(verb=movement_target)
        return Command(verb=verb, target=target)


class CommandRegistry:
    """Maps verb strings to handler functions."""

    def __init__(self, unknown_message: str | None = None) -> None:
        """Initialise an empty registry.

        Parameters
        ----------
        unknown_message : str, optional
            ``str.format``-compatible template shown when the player types a
            verb with no registered handler.  The token ``{verb}`` is
            substituted with the unrecognised verb.  Defaults to a built-in
            fallback so the registry can be instantiated without a YAML
            dependency (useful for unit tests).
        """
        self._handlers: dict[str, CommandHandler] = {}
        self._unknown_message = (
            unknown_message or load_yaml_data("commands.yaml")["responses"]["unknown"]
        )

    def register(self, verb: str, handler: CommandHandler) -> None:
        """Associate *verb* (case-insensitive) with *handler*.

        Parameters
        ----------
        verb : str
            The command keyword to register (normalised to lower-case).
        handler : CommandHandler
            Callable ``(verb, target, state) -> str`` invoked when a player
            command with this verb is dispatched.
        """
        self._handlers[verb.lower()] = handler

    def dispatch(self, command: Command, state: "GameState") -> str:
        """Look up *command.verb* and call its handler; return its message.

        Parameters
        ----------
        command : Command
            The parsed player command produced by :class:`CommandParser`.
        state : GameState
            The live game state forwarded unchanged to the handler.

        Returns
        -------
        str
            The message string produced by the handler, or an
            ``unknown_message`` fallback when the verb is not registered.
        """
        handler = self._handlers.get(command.verb)
        if handler is None:
            return self._unknown_message.format(verb=command.verb)
        return handler(command.verb, command.target, state)

    def known_verbs(self) -> list[str]:
        """Return a sorted list of every registered verb.

        Returns
        -------
        list[str]
            All registered verb strings sorted in ascending alphabetical order.
        """
        return sorted(self._handlers.keys())


def register_target_state_handler(
    registry: CommandRegistry, handler: TargetStateHandler, *verbs: str
) -> None:
    """Register one ``(target, state)`` handler under one or more verbs.

    Parameters
    ----------
    registry : CommandRegistry
        Registry receiving the adapted command handlers.
    handler : TargetStateHandler
        Simpler callable that does not care which verb triggered it.
    *verbs : str
        Command verbs that should delegate to *handler*.
    """

    def handle_registered_command(
        _verb: str, target: str | None, state: "GameState"
    ) -> str:
        """Discard the registry verb and delegate to the shared handler."""
        return handler(target, state)

    for verb in verbs:
        registry.register(verb, handle_registered_command)


def register_target_state_command_specs(
    registry: CommandRegistry,
    command_specs: tuple[TargetStateCommandSpec, ...],
) -> None:
    """Register multiple simple ``(target, state)`` handlers from declarative specs."""
    for verbs, handler in command_specs:
        register_target_state_handler(registry, handler, *verbs)


def register_room_state_handler(
    registry: CommandRegistry,
    current_room: CurrentRoomProvider,
    room_id: str,
    missing_response: str,
    handler: RoomStateHandler,
    *verbs: str,
) -> None:
    """Register one room-gated ``(room, state)`` handler under one or more verbs.

    Parameters
    ----------
    registry : CommandRegistry
        Registry receiving the adapted command handlers.
    current_room : CurrentRoomProvider
        Zero-argument callable returning the live current room, or ``None``
        when the engine is unavailable.
    room_id : str
        ``room_id`` where the handler is allowed to run.
    missing_response : str
        Response returned when the player is not currently in ``room_id``.
    handler : RoomStateHandler
        Callable that receives the live room object plus mutable game state.
    *verbs : str
        Command verbs that should delegate to *handler* when the room gate
        passes.
    """

    def handle_room_action(_target: str | None, state: "GameState") -> str:
        """Run the room-aware handler only when the player is in ``room_id``."""
        room = current_room()
        if room is None or room.room_id != room_id:
            return missing_response
        return handler(room, state)

    register_target_state_handler(registry, handle_room_action, *verbs)


def fixed_room_state_handler(response: str) -> RoomStateHandler:
    """Return a room/state handler that always yields the same response.

    Useful when a room-target command spec should return one static string but
    still needs to satisfy the shared ``RoomStateHandler`` protocol.
    """

    def handle_fixed_response(_room: "Room", _state: "GameState") -> str:
        """Ignore room and state, returning the preselected response."""
        return response

    return handle_fixed_response


def state_only_room_state_handler(handler: StateOnlyHandler) -> RoomStateHandler:
    """Adapt a ``(state) -> str`` formatter to the room/state handler protocol."""

    def handle_state_only(_room: "Room", state: "GameState") -> str:
        """Ignore the room and delegate to the wrapped state-only handler."""
        return handler(state)

    return handle_state_only


def register_room_state_command_specs(
    registry: CommandRegistry,
    current_room: CurrentRoomProvider,
    command_specs: tuple[RoomStateCommandSpec, ...],
) -> None:
    """Register multiple room-gated command families from declarative specs."""
    for verbs, room_id, missing_response, handler in command_specs:
        register_room_state_handler(
            registry,
            current_room,
            room_id,
            missing_response,
            handler,
            *verbs,
        )


def register_room_target_state_handler(
    registry: CommandRegistry,
    current_room: CurrentRoomProvider,
    handlers: Mapping[tuple[str, str], RoomStateHandler],
    fallback: TargetStateHandler,
    *verbs: str,
) -> None:
    """Register verbs that try room-target handlers before a generic fallback.

    Parameters
    ----------
    registry : CommandRegistry
        Registry receiving the adapted command handlers.
    current_room : CurrentRoomProvider
        Zero-argument callable returning the live current room, or ``None``
        when the engine is unavailable.
    handlers : Mapping[tuple[str, str], RoomStateHandler]
        Mapping of ``(room_id, target)`` to room-aware handlers.
    fallback : TargetStateHandler
        Generic target/state handler used when no room-target match exists.
    *verbs : str
        Command verbs that should delegate to the room-target flow.
    """

    def handle_room_target(target: str | None, state: "GameState") -> str:
        """Dispatch on ``(room_id, target)`` before falling back."""
        room = current_room()
        if room is not None and target is not None:
            handler = handlers.get((room.room_id, target))
            if handler is not None:
                return handler(room, state)
        return fallback(target, state)

    register_target_state_handler(registry, handle_room_target, *verbs)


def register_room_target_command_specs(
    registry: CommandRegistry,
    current_room: CurrentRoomProvider,
    command_specs: tuple[RoomTargetCommandSpec, ...],
) -> None:
    """Register multiple room-target command families from declarative specs."""
    for verbs, handlers, fallback in command_specs:
        register_room_target_state_handler(
            registry,
            current_room,
            handlers,
            fallback,
            *verbs,
        )
