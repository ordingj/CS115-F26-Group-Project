"""Command asset type, parser, and dispatch registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

import yaml

if TYPE_CHECKING:
    from game.state import GameState

_CMD: dict = yaml.safe_load(
    (Path(__file__).parent.parent / "data" / "commands.yaml").read_text(encoding="utf-8")
)["responses"]

# ── canonical verb sets ───────────────────────────────────────────────────────

MOVEMENT_VERBS: frozenset[str] = frozenset({"forward", "back", "left", "right"})

ACTION_VERBS: frozenset[str] = frozenset(
    {
        "look",
        "examine",
        "read",
        "open",
        "knock",
        "listen",
        "wash",
        "check",
        "help",
        "quit",
    }
)

# Handler: (verb, target, state) -> message string shown to the player.
CommandHandler = Callable[[str, Optional[str], "GameState"], str]


@dataclass
class Command:
    """A parsed player command.

    Attributes:
        verb:   The action word (e.g. ``"forward"``, ``"read"``).
        target: Optional object the action is directed at (e.g. ``"sign"``).
    """

    verb: str
    target: Optional[str] = None  # e.g. "sign", "watch", "door"


class CommandParser:
    """Converts raw player input into a :class:`Command` object."""

    def parse(self, raw: str) -> Command:
        """Tokenise *raw* input and return a :class:`Command`.

        The first token becomes the verb; any remaining tokens are joined as
        the target.  An empty string produces ``Command(verb="")``.
        """
        tokens = raw.strip().lower().split()
        if not tokens:
            return Command(verb="")
        verb = tokens[0]
        target = " ".join(tokens[1:]) if len(tokens) > 1 else None
        return Command(verb=verb, target=target)


class CommandRegistry:
    """Maps verb strings to handler functions."""

    def __init__(self) -> None:
        """Initialise an empty registry."""
        self._handlers: dict[str, CommandHandler] = {}

    def register(self, verb: str, handler: CommandHandler) -> None:
        """Associate *verb* (case-insensitive) with *handler*."""
        self._handlers[verb.lower()] = handler

    def dispatch(self, command: Command, state: "GameState") -> str:
        """Look up *command.verb* and call its handler; return its message.

        Returns an "unknown command" message when the verb is not registered.
        """
        handler = self._handlers.get(command.verb)
        if handler is None:
            return _CMD["unknown"].format(verb=command.verb)
        return handler(command.verb, command.target, state)

    def known_verbs(self) -> list[str]:
        """Return a sorted list of every registered verb."""
        return sorted(self._handlers.keys())
