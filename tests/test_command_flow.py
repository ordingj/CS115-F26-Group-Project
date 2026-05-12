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
                "dry",
                "drop",
                "exit",
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
        """Verify edge-case handling for read, open, knock, check, help, and quit aliases."""
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

        exit_engine = make_engine()
        exit_result = dispatch(exit_engine, "exit")

        self.assertEqual(exit_result, "You give up and head home. Game over.")
        self.assertTrue(exit_engine.state.quit)
        self.assertTrue(exit_engine.state.game_over)

    def test_read_flyer_uses_active_step1_sign_clue(self) -> None:
        """Verify that READ FLYER works at the 4-way only when the flyer clue is active."""
        engine = make_engine(start_room="intersection_4way")
        engine.state.active_clues.update(
            {
                "step1_correct_dir": "left",
                "step1_clue_type": "sign",
            }
        )

        result = dispatch(engine, "read", "flyer")

        self.assertIn("CS CLUB BAKE SALE", result)
        self.assertIn("pointing left", result)

    def test_room_gated_commands_return_missing_location_responses(self) -> None:
        """Verify that bathroom and janitor verbs still return their out-of-room fallback text."""
        engine = make_engine(start_room="lobby")

        self.assertEqual(
            dispatch(engine, "rinse", "hands"), "There's nothing to rinse here."
        )
        self.assertEqual(
            dispatch(engine, "wash", "hands"), "There's nothing to rinse here."
        )
        self.assertEqual(dispatch(engine, "stop"), "There's nothing to stop here.")
        self.assertEqual(
            dispatch(engine, "soap", "hands"), "There's no soap dispenser here."
        )
        self.assertEqual(
            dispatch(engine, "dry", "hands"), "There's nothing to dry here."
        )
        self.assertEqual(
            dispatch(engine, "listen"),
            "You listen carefully. The building hums with an uneasy silence.",
        )

    def test_dry_hands_in_bathroom_reports_missing_paper_towel_handle(self) -> None:
        """Verify that DRY HANDS in the bathroom returns the dispenser flavor text."""
        engine = make_engine(start_room="bathroom")

        result = dispatch(engine, "dry", "hands")

        self.assertEqual(result, "The paper towel dispenser's handle is missing.")


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
