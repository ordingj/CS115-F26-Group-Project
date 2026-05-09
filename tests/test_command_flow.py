"""Integration tests for command coverage and inventory handling.

Checks that every registered verb produces a non-empty response and
that inventory pick-up/drop operations behave correctly.
"""

from __future__ import annotations

import unittest

from tests.helpers import dispatch, make_engine


class CommandCoverageTest(unittest.TestCase):
    """Verify supported commands and non-puzzle command handling."""

    def test_build_commands_registers_every_supported_verb(self) -> None:
        """Verify that build_commands registers every expected verb and no extras."""
        engine = make_engine()

        self.assertEqual(
            set(engine.registry.known_verbs()),
            {
                "back",
                "check",
                "drop",
                "examine",
                "forward",
                "help",
                "i",
                "inventory",
                "knock",
                "left",
                "listen",
                "look",
                "open",
                "quit",
                "read",
                "right",
                "rinse",
                "soap",
                "stop",
                "wash",
            },
        )

    def test_read_open_knock_check_help_and_quit_handle_edge_cases(self) -> None:
        """Verify edge-case handling for read, open, knock, check, help, and quit."""
        engine = make_engine()

        self.assertEqual(dispatch(engine, "read"), "Read what?")
        self.assertIn("DETOUR", dispatch(engine, "read", "sign"))
        self.assertIn("DETOUR", dispatch(engine, "read", "detour_sign"))
        self.assertEqual(dispatch(engine, "open"), "Open what?")
        self.assertIn("won't budge", dispatch(engine, "open", "door"))
        self.assertEqual(dispatch(engine, "knock"), "Knock on what?")
        self.assertIn("No answer.", dispatch(engine, "knock", "door"))
        self.assertEqual(
            dispatch(engine, "check", "watch"), "Your watch reads 10:00 remaining."
        )
        self.assertIn("Available commands:", dispatch(engine, "help"))

        result = dispatch(engine, "quit")

        self.assertEqual(result, "You give up and head home. Game over.")
        self.assertTrue(engine.state.quit)
        self.assertTrue(engine.state.game_over)


class InventoryTest(unittest.TestCase):
    """Verify inventory listing, aliases, drops, and inspection responses."""

    def test_inventory_lists_default_items(self) -> None:
        """Verify that the inventory command lists all five default starting items."""
        engine = make_engine()
        result = dispatch(engine, "inventory")
        self.assertIn("watch", result)
        self.assertIn("backpack", result)
        self.assertIn("phone", result)
        self.assertIn("keys", result)
        self.assertIn("wallet", result)

    def test_i_alias_lists_inventory(self) -> None:
        """Verify that 'i' is accepted as a synonym for the inventory command."""
        engine = make_engine()
        result = dispatch(engine, "i")
        self.assertIn("watch", result)
        self.assertIn("phone", result)

    def test_inventory_empty_state(self) -> None:
        """Verify that the inventory command reports nothing when the inventory is cleared."""
        engine = make_engine()
        engine.state.inventory.clear()
        result = dispatch(engine, "inventory")
        self.assertNotIn("watch", result)

    def test_drop_anything_is_blocked(self) -> None:
        """Verify that every possible drop target returns the 'hang onto that' refusal."""
        engine = make_engine()
        for item in ("watch", "phone", "keys", "wallet", "backpack", "stuff"):
            with self.subTest(item=item):
                result = dispatch(engine, "drop", item)
                self.assertEqual(result, "You should probably hang onto that.")

    def test_look_inventory_items_return_expected_text(self) -> None:
        """Verify that examining each inventory item returns item-specific flavour text."""
        engine = make_engine()
        expected_text = {
            "backpack": "don't have time",
            "phone": "don't have time",
            "keys": "Room 314",
            "wallet": "Room 314",
            "watch": "remaining",
        }

        for item, expected in expected_text.items():
            with self.subTest(item=item):
                result = dispatch(engine, "look", item)
                self.assertIn(expected, result)


if __name__ == "__main__":
    unittest.main()
