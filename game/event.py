"""Event asset type and queue for time- and state-driven narrative beats.

:func:`load_events` reads ``data/events.yaml`` and returns a populated
:class:`EventQueue` using :func:`_build_condition` to convert each
declarative condition spec into a callable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import yaml

if TYPE_CHECKING:
    from game.state import GameState

_EVENTS_FILE = Path(__file__).parent.parent / "data" / "events.yaml"

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


# ── YAML loader ────────────────────────────────────────────────────────────────


def _build_condition(spec: dict[str, Any]) -> EventCondition:
    """Convert a declarative condition spec (from YAML) into a callable.

    Supported types
    ---------------
    ``time_range``      – ``gt < state.time_remaining <= lte``
    ``move_count_eq``   – ``state.move_count == value``
    ``move_count_gte``  – ``state.move_count >= value``
    ``location``        – ``state.current_room_id == room_id``
    ``wrong_turns_gte`` – ``state.wrong_turns >= value``
    ``all``             – all sub-conditions true (list under ``conditions``)
    """
    ctype = spec["type"]
    if ctype == "time_range":
        gt, lte = int(spec["gt"]), int(spec["lte"])
        return lambda s: gt < s.time_remaining <= lte
    if ctype == "move_count_eq":
        val = int(spec["value"])
        return lambda s: s.move_count == val
    if ctype == "move_count_gte":
        val = int(spec["value"])
        return lambda s: s.move_count >= val
    if ctype == "location":
        room_id = str(spec["room_id"])
        return lambda s: s.current_room_id == room_id
    if ctype == "wrong_turns_gte":
        val = int(spec["value"])
        return lambda s: s.wrong_turns >= val
    if ctype == "all":
        sub = [_build_condition(c) for c in spec["conditions"]]
        return lambda s: all(c(s) for c in sub)
    raise ValueError(f"Unknown condition type: {ctype!r}")


def load_events() -> EventQueue:
    """Parse ``data/events.yaml`` and return a populated :class:`EventQueue`."""
    raw: dict = yaml.safe_load(_EVENTS_FILE.read_text(encoding="utf-8"))
    queue = EventQueue()
    for entry in raw["events"]:
        queue.register(
            Event(
                event_id=entry["event_id"],
                message=entry["message"],
                condition=_build_condition(entry["condition"]),
            )
        )
    return queue
