"""Regression tests for world-building helpers.

Ensures that :func:`~game.world.build_world` produces correctly connected,
mutably isolated room instances on every call.
"""

from __future__ import annotations

import unittest

from game.world import build_world


class BuildWorldIsolationTest(unittest.TestCase):
    """Ensure each world build gets fresh room instances."""

    def test_build_world_clones_mutable_room_state(self) -> None:
        """Mutating one built world must not affect the next build."""
        world = build_world()
        world["bathroom"].attributes["wash_phase"] = 99
        world["intersection_4way"].exits["left"] = "mutated"

        rebuilt = build_world()

        self.assertNotEqual(rebuilt["bathroom"].attributes.get("wash_phase"), 99)
        self.assertNotEqual(rebuilt["intersection_4way"].exits.get("left"), "mutated")
        self.assertIsNot(world["bathroom"], rebuilt["bathroom"])

    def test_build_world_keeps_expected_room_connections(self) -> None:
        """Every shipped room should expose the intended base exit layout."""
        world = build_world()

        expected_exits = {
            "lobby": {
                "forward": "__lobby_forward_blocked__",
                "left": "hallway_approach",
                "back": "__lobby_back_blocked__",
            },
            "hallway_approach": {"forward": "intersection_4way", "back": None},
            "intersection_4way": {
                "forward": None,
                "back": "hallway_approach",
                "left": None,
                "right": None,
            },
            "intersection_3way": {
                "forward": "bathroom",
                "left": None,
                "right": None,
                "back": "intersection_4way",
            },
            "bathroom": {"back": "intersection_3way_exit"},
            "intersection_3way_exit": {
                "back": "bathroom",
                "left": None,
                "right": None,
                "forward": None,
            },
            "hallway_janitor": {
                "back": "intersection_3way_exit",
                "left": None,
                "right": None,
                "forward": None,
            },
            "hallway_final": {"back": "hallway_janitor", "forward": "room_314"},
            "room_314": {},
            "flavor_copy_room": {"forward": "intersection_4way", "back": None},
            "flavor_faculty_office": {"forward": "intersection_4way", "back": None},
            "flavor_study_lounge": {"forward": "intersection_4way", "back": None},
            "flavor_stairwell": {"forward": "intersection_4way", "back": None},
            "flavor_classroom_195": {"forward": "intersection_4way", "back": None},
            "flavor_water_fountain": {"forward": "intersection_4way", "back": None},
        }

        for room_id, exits in expected_exits.items():
            with self.subTest(room_id=room_id):
                self.assertEqual(world[room_id].exits, exits)


if __name__ == "__main__":
    unittest.main()
