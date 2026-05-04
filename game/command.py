"""Command asset type, parser, and dispatch registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from game.state import GameState

# ── canonical verb sets ───────────────────────────────────────────────────────

MOVEMENT_VERBS: frozenset[str] = frozenset({"forward", "back", "left", "right"})

ACTION_VERBS: frozenset[str] = frozenset({
    "look", "examine", "read", "open", "knock",
    "listen", "wash", "check", "help", "quit",
})

# Handler: (verb, target, state) -> message string shown to the player.
CommandHandler = Callable[[str, Optional[str], "GameState"], str]


@dataclass
class Command:
    """A parsed player command."""

    verb: str
    target: Optional[str] = None  # e.g. "sign", "watch", "door"


class CommandParser:
    """Converts raw player input into a Command object."""

    def parse(self, raw: str) -> Command:
        tokens = raw.strip().lower().split()
        if not tokens:
            return Command(verb="")
        verb = tokens[0]
        target = " ".join(tokens[1:]) if len(tokens) > 1 else None
        return Command(verb=verb, target=target)


class CommandRegistry:
    """Maps verb strings to handler functions."""

    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandler] = {}

    def register(self, verb: str, handler: CommandHandler) -> None:
        self._handlers[verb.lower()] = handler

    def dispatch(self, command: Command, state: "GameState") -> str:
        handler = self._handlers.get(command.verb)
        if handler is None:
            return f"I don't know how to '{command.verb}'."
        return handler(command.verb, command.target, state)

    def known_verbs(self) -> list[str]:
        return sorted(self._handlers.keys())
