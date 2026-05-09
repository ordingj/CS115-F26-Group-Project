"""Event asset type and queue for time- and state-driven narrative beats.

:func:`load_events` reads ``data/events.yaml`` and returns a populated
:class:`EventQueue` using :func:`_build_condition` to convert each
declarative condition spec into a callable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import operator
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from game import load_yaml_data

if TYPE_CHECKING:
    from game.state import GameState

# Condition: (state) -> bool – True when the event should fire.
EventCondition = Callable[["GameState"], bool]
ConditionBuilder = Callable[[dict[str, Any]], EventCondition]


def _time_range_condition(gt: int, lte: int) -> EventCondition:
    """Return a condition for ``gt < time_remaining <= lte``.

    Parameters
    ----------
    gt : int
        Exclusive lower bound in seconds.
    lte : int
        Inclusive upper bound in seconds.

    Returns
    -------
    EventCondition
        Callable that takes a :class:`~game.state.GameState` and returns
        ``True`` while ``time_remaining`` is within the range.
    """
    return lambda s: gt < s.time_remaining <= lte


def _field_condition(
    field: str, value: Any, comparator: Callable[[Any, Any], bool]
) -> EventCondition:
    """Return a condition that compares one ``GameState`` attribute against *value*.

    Parameters
    ----------
    field : str
        Attribute name on :class:`~game.state.GameState` to read (e.g.
        ``"move_count"``).
    value : Any
        Value to compare against.
    comparator : Callable[[Any, Any], bool]
        Binary comparison function from the :mod:`operator` module (e.g.
        ``operator.eq``, ``operator.ge``).

    Returns
    -------
    EventCondition
        Callable ``(state) -> bool``.
    """
    return lambda s: comparator(getattr(s, field), value)


def _all_conditions(specs: list[dict[str, Any]]) -> EventCondition:
    """Return a condition that requires every nested condition to pass.

    Used to implement the ``"all"`` compound condition type, where the YAML
    supplies a ``conditions`` list of sub-specs that must all be ``True``.

    Parameters
    ----------
    specs : list[dict[str, Any]]
        List of raw condition spec dicts (each will be passed to
        :func:`_build_condition`).

    Returns
    -------
    EventCondition
        Callable that returns ``True`` only when every sub-condition returns
        ``True``.
    """
    subconditions = [_build_condition(spec) for spec in specs]
    return lambda s: all(condition(s) for condition in subconditions)


def _field_condition_builder(
    field: str,
    spec_key: str,
    value_reader: Callable[[Any], Any],
    comparator: Callable[[Any, Any], bool],
) -> ConditionBuilder:
    """Build a YAML condition parser for one GameState field comparison.

    Parameters
    ----------
    field : str
        Attribute name on :class:`~game.state.GameState` to compare.
    spec_key : str
        Key to read from the raw YAML condition spec.
    value_reader : Callable[[Any], Any]
        Normaliser used to coerce the raw spec value (for example ``int`` or
        ``str``).
    comparator : Callable[[Any, Any], bool]
        Binary comparison used by :func:`_field_condition`.

    Returns
    -------
    ConditionBuilder
        Builder that converts one raw condition spec into an
        :class:`EventCondition`.
    """

    def build_field_condition(spec: dict[str, Any]) -> EventCondition:
        """Parse one YAML spec and return the configured field comparison."""
        return _field_condition(field, value_reader(spec[spec_key]), comparator)

    return build_field_condition


_FIELD_CONDITION_SPECS: dict[
    str, tuple[str, str, Callable[[Any], Any], Callable[[Any, Any], bool]]
] = {
    "move_count_eq": ("move_count", "value", int, operator.eq),
    "move_count_gte": ("move_count", "value", int, operator.ge),
    "location": ("current_room_id", "room_id", str, operator.eq),
    "wrong_turns_gte": ("wrong_turns", "value", int, operator.ge),
}


_CONDITION_BUILDERS: dict[str, ConditionBuilder] = {
    "time_range": lambda spec: _time_range_condition(int(spec["gt"]), int(spec["lte"])),
    "all": lambda spec: _all_conditions(spec["conditions"]),
    **{
        condition_type: _field_condition_builder(
            field,
            spec_key,
            value_reader,
            comparator,
        )
        for condition_type, (
            field,
            spec_key,
            value_reader,
            comparator,
        ) in _FIELD_CONDITION_SPECS.items()
    },
}


@dataclass
class Event:
    """A narrative event that fires when its condition becomes true.

    Attributes
    ----------
    event_id : str
        Unique identifier used for deduplication and debug logging.
    message : str
        Text presented to the player when this event fires.
    condition : EventCondition
        Callable ``(state) -> bool`` built from a YAML spec by
        :func:`_build_condition`.
    one_shot : bool
        When ``True`` (the default) the event fires at most once per game
        session.  After firing it is pruned from the queue by
        :meth:`EventQueue.tick`.
    """

    event_id: str
    message: str
    condition: EventCondition
    one_shot: bool = True
    _fired: bool = field(default=False, init=False, repr=False)

    def should_fire(self, state: "GameState") -> bool:
        """Return ``True`` if this event's condition is met and it may still fire.

        Parameters
        ----------
        state : GameState
            Current game state passed to the condition callable.

        Returns
        -------
        bool
            ``False`` if this is a one-shot event that has already fired;
            otherwise the result of evaluating the condition.
        """
        if self.one_shot and self._fired:
            return False
        return self.condition(state)

    def fire(self) -> str:
        """Mark the event as fired and return its message string.

        Returns
        -------
        str
            The event's message, ready to display to the player.
        """
        self._fired = True
        return self.message


class EventQueue:
    """Evaluates registered events each game tick and collects their output.

    All events are checked on every call to :meth:`tick`; one-shot events
    are automatically pruned after they fire so subsequent ticks skip them.
    """

    def __init__(self) -> None:
        """Initialise an empty event queue."""
        self._events: list[Event] = []

    def register(self, event: Event) -> None:
        """Add *event* to the queue so it will be evaluated each tick.

        Parameters
        ----------
        event : Event
            Event instance to register.
        """
        self._events.append(event)

    def tick(self, state: "GameState") -> list[str]:
        """Return messages for all events whose conditions are currently met.

        Parameters
        ----------
        state : GameState
            The current game state evaluated against each event's condition.

        Returns
        -------
        list[str]
            Messages from every event that fired this tick, in registration
            order.  One-shot events that just fired are pruned afterwards.
        """
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

    Parameters
    ----------
    spec : dict[str, Any]
        Condition spec mapping from ``data/events.yaml``.  Must contain a
        ``"type"`` key; additional keys depend on the type.

    Returns
    -------
    EventCondition
        Callable ``(state) -> bool`` appropriate for the spec type.

    Raises
    ------
    ValueError
        If ``spec["type"]`` is not in :data:`_CONDITION_BUILDERS`.

    Notes
    -----
    Supported condition types and their required keys:

    ``time_range``
        ``gt`` (exclusive lower bound), ``lte`` (inclusive upper bound) in
        seconds.
    ``move_count_eq``
        ``value`` — fires when ``move_count == value``.
    ``move_count_gte``
        ``value`` — fires when ``move_count >= value``.
    ``location``
        ``room_id`` — fires when the player is in that room.
    ``wrong_turns_gte``
        ``value`` — fires when ``wrong_turns >= value``.
    ``all``
        ``conditions`` — list of nested condition specs (all must be true).
    """
    ctype = spec["type"]
    builder = _CONDITION_BUILDERS.get(ctype)
    if builder is not None:
        return builder(spec)
    raise ValueError(f"Unknown condition type: {ctype!r}")


def load_events() -> EventQueue:
    """Parse ``data/events.yaml`` and return a populated :class:`EventQueue`.

    Returns
    -------
    EventQueue
        Queue pre-populated with one :class:`Event` per YAML entry.
    """
    raw: dict[str, Any] = load_yaml_data("events.yaml")
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
