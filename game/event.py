"""Event asset type and queue for time- and state-driven narrative beats.

:func:`load_events` reads ``data/events.yaml`` and returns a populated
:class:`EventQueue` using :func:`_build_condition` to convert each
declarative condition spec into a callable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
import operator
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from game import load_yaml_data

if TYPE_CHECKING:
    from game.state import GameState

# Condition: (state) -> bool – True when the event should fire.
EventCondition = Callable[["GameState"], bool]
ConditionBuilder = Callable[[dict[str, Any]], EventCondition]
SpecValueReader = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class _ConditionBuilderSpec:
    """Declarative description of how one YAML condition type is parsed."""

    factory: Callable[..., EventCondition]
    arg_readers: tuple[SpecValueReader, ...]


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


def _spec_value_reader(
    key: str,
    value_reader: Callable[[Any], Any] | None = None,
) -> SpecValueReader:
    """Return a reader for one raw YAML condition field.

    Parameters
    ----------
    key : str
        Raw YAML key to read from the condition spec.
    value_reader : Callable[[Any], Any] or None, optional
        Optional coercion function applied to the raw value.

    Returns
    -------
    SpecValueReader
        Callable that extracts one argument value from a raw condition spec.
    """

    def read_spec_value(spec: dict[str, Any]) -> Any:
        """Extract and optionally coerce one value from *spec*."""
        value = spec[key]
        return value_reader(value) if value_reader is not None else value

    return read_spec_value


def _condition_builder(builder_spec: _ConditionBuilderSpec) -> ConditionBuilder:
    """Build one YAML condition parser from a declarative builder spec.

    Parameters
    ----------
    builder_spec : _ConditionBuilderSpec
        Declarative condition builder description.

    Returns
    -------
    ConditionBuilder
        Builder that reads the required raw spec fields and passes them to the
        configured condition factory.
    """

    def build_condition(spec: dict[str, Any]) -> EventCondition:
        """Parse one YAML spec through the configured value readers."""
        return builder_spec.factory(
            *(reader(spec) for reader in builder_spec.arg_readers)
        )

    return build_condition


_FIELD_CONDITION_SPECS: dict[
    str, tuple[str, str, Callable[[Any], Any], Callable[[Any, Any], bool]]
] = {
    "move_count_eq": ("move_count", "value", int, operator.eq),
    "move_count_gte": ("move_count", "value", int, operator.ge),
    "location": ("current_room_id", "room_id", str, operator.eq),
    "wrong_turns_gte": ("wrong_turns", "value", int, operator.ge),
}


_CONDITION_BUILDER_SPECS: dict[str, _ConditionBuilderSpec] = {
    "time_range": _ConditionBuilderSpec(
        _time_range_condition,
        (
            _spec_value_reader("gt", int),
            _spec_value_reader("lte", int),
        ),
    ),
    "all": _ConditionBuilderSpec(
        _all_conditions,
        (_spec_value_reader("conditions"),),
    ),
    **{
        condition_type: _ConditionBuilderSpec(
            partial(_field_condition, field, comparator=comparator),
            (_spec_value_reader(spec_key, value_reader),),
        )
        for condition_type, (
            field,
            spec_key,
            value_reader,
            comparator,
        ) in _FIELD_CONDITION_SPECS.items()
    },
}


_CONDITION_BUILDERS: dict[str, ConditionBuilder] = {
    condition_type: _condition_builder(builder_spec)
    for condition_type, builder_spec in _CONDITION_BUILDER_SPECS.items()
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
