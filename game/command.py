"""Command asset type, parser, and dispatch registry."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.state import GameState

# ── canonical verb sets ───────────────────────────────────────────────────────

MOVEMENT_VERBS: frozenset[str] = frozenset({"forward", "back", "left", "right"})

# Handler: (verb, target, state) -> message string shown to the player.
CommandHandler = Callable[[str, "str | None", "GameState"], str]
TargetStateHandler = Callable[["str | None", "GameState"], str]


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
        are joined with spaces to form the target.  An empty or
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
        verb = tokens[0]
        # Collapse all remaining tokens into one target string (e.g.
        # "read detour sign" → target="detour sign").
        target = " ".join(tokens[1:]) if len(tokens) > 1 else None
        # "go <direction>" is a common natural-language form.  Re-map it so
        # downstream handlers only need to handle bare direction verbs.
        if verb == "go" and target in MOVEMENT_VERBS:
            return Command(verb=target)
        return Command(verb=verb, target=target)


class CommandRegistry:
    """Maps verb strings to handler functions."""

    def __init__(self, unknown_message: str = "I don't know how to '{verb}'.") -> None:
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
        self._unknown_message = unknown_message

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
