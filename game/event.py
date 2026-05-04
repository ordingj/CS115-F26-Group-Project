"""Event asset type and queue for time- and state-driven narrative beats."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from game.state import GameState

# Condition: (state) -> bool – True when the event should fire.
EventCondition = Callable[["GameState"], bool]


@dataclass
class Event:
    """A narrative event that fires when its condition becomes true.

    Attributes:
        event_id:  Unique identifier (used for deduplication / debugging).
        message:   Text printed to the player when the event fires.
        condition: Callable that returns True when the event should trigger.
        one_shot:  If True, the event fires at most once per game session.
    """

    event_id: str
    message: str
    condition: EventCondition
    one_shot: bool = True
    _fired: bool = field(default=False, init=False, repr=False)

    def should_fire(self, state: "GameState") -> bool:
        if self.one_shot and self._fired:
            return False
        return self.condition(state)

    def fire(self) -> str:
        self._fired = True
        return self.message


class EventQueue:
    """Evaluates registered events each game tick and collects their output."""

    def __init__(self) -> None:
        self._events: list[Event] = []

    def register(self, event: Event) -> None:
        self._events.append(event)

    def tick(self, state: "GameState") -> list[str]:
        """Return messages for all events whose conditions are currently met."""
        messages: list[str] = []
        for event in self._events:
            if event.should_fire(state):
                messages.append(event.fire())
        # Prune exhausted one-shot events.
        self._events = [e for e in self._events if not (e.one_shot and e._fired)]
        return messages
