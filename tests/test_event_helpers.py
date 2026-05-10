"""Unit tests for event condition and queue helper behavior."""

from __future__ import annotations

import unittest

from game.event import Event, EventQueue, _build_condition, load_events
from game.state import GameState


class EventQueueTest(unittest.TestCase):
    """Verify declarative event conditions and queue behaviour."""

    def test_build_condition_supports_leaf_condition_specs(self) -> None:
        """Verify that each declared leaf condition type still evaluates through the shared builder path."""
        state = GameState(current_room_id="bathroom", time_remaining=175)
        state.move_count = 2
        state.wrong_turns = 1

        cases = (
            ("time_range", {"type": "time_range", "gt": 165, "lte": 180}, True),
            (
                "time_range_lower_bound",
                {"type": "time_range", "gt": 175, "lte": 180},
                False,
            ),
            ("move_count_eq", {"type": "move_count_eq", "value": 2}, True),
            ("move_count_gte", {"type": "move_count_gte", "value": 2}, True),
            ("location", {"type": "location", "room_id": "bathroom"}, True),
            (
                "wrong_turns_gte",
                {"type": "wrong_turns_gte", "value": 1},
                True,
            ),
        )

        for label, spec, expected in cases:
            with self.subTest(condition_type=label):
                self.assertIs(_build_condition(spec)(state), expected)

    def test_build_condition_supports_composed_specs(self) -> None:
        """Verify that an 'all' condition type correctly ANDs time, location, move, and wrong-turn sub-conditions."""
        state = GameState(current_room_id="bathroom", time_remaining=175)
        state.move_count = 2
        state.wrong_turns = 1

        condition = _build_condition(
            {
                "type": "all",
                "conditions": [
                    {"type": "time_range", "gt": 165, "lte": 180},
                    {"type": "location", "room_id": "bathroom"},
                    {"type": "move_count_gte", "value": 2},
                    {"type": "wrong_turns_gte", "value": 1},
                ],
            }
        )

        self.assertTrue(condition(state))

    def test_build_condition_rejects_unknown_types(self) -> None:
        """Verify that _build_condition raises ValueError for unrecognised condition type strings."""
        with self.assertRaises(ValueError):
            _build_condition({"type": "mystery"})

    def test_event_queue_prunes_fired_one_shot_events(self) -> None:
        """Verify that one-shot events fire exactly once while always-on events fire every tick."""
        state = GameState(current_room_id="lobby")
        queue = EventQueue()
        queue.register(Event("once", "first", lambda _: True))
        queue.register(Event("always", "repeat", lambda _: True, one_shot=False))

        first = queue.tick(state)
        second = queue.tick(state)

        self.assertEqual(first, ["first", "repeat"])
        self.assertEqual(second, ["repeat"])

    def test_load_events_builds_live_conditions_from_yaml(self) -> None:
        """Verify that load_events() returns a queue whose conditions fire against live GameState values."""
        state = GameState(current_room_id="lobby", time_remaining=300)
        state.move_count = 1

        messages = load_events().tick(state)

        self.assertIn(
            "Your phone buzzes. A calendar reminder: exam starts in 5 minutes.",
            messages,
        )
        self.assertIn(
            "You notice the ceiling tiles above are slightly misaligned, like they've been recently\n      disturbed.".replace(
                "\n      ", " "
            ),
            messages,
        )


if __name__ == "__main__":
    unittest.main()
