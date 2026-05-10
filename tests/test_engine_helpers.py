"""Unit tests for plain-engine room rendering and loop helper behavior."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from game.engine import UI
from tests.helpers import make_engine, make_intersection_engine


class GameEngineFormattingTest(unittest.TestCase):
    """Verify shared room-presentation helpers used by the plain-text UI."""

    def test_current_room_view_collects_dynamic_clues_and_metadata(self) -> None:
        """Verify that _current_room_view assembles clue text, exits, items, and formatted time."""
        engine, room = make_intersection_engine()

        room_view = engine._current_room_view()

        self.assertIsNotNone(room_view)
        assert room_view is not None
        self.assertEqual(room_view.name, room.name)
        self.assertEqual(room_view.description, room.description)
        self.assertIn("right hallway", room_view.clue)
        self.assertEqual(room_view.exits, ("left", "right"))
        self.assertEqual(room_view.items, ("exam poster",))
        self.assertEqual(room_view.time_remaining, "2:05")

    def test_current_room_view_uses_shared_janitor_hint_helper(self) -> None:
        """Verify that the janitor hallway clue comes through the shared janitor formatter."""
        engine = make_engine(start_room="hallway_janitor", time_remaining=240)
        engine.state.active_clues["step3_song_chorus"] = (
            "Take the left hall\nTake it again\nOne more line"
        )

        room_view = engine._current_room_view()

        self.assertIsNotNone(room_view)
        assert room_view is not None
        self.assertIn("The janitor is humming.", room_view.clue)
        self.assertIn("Take the left hall", room_view.clue)
        self.assertIn("Take it again", room_view.clue)
        self.assertNotIn("One more line", room_view.clue)

    def test_current_room_clue_returns_blank_for_non_clue_rooms(self) -> None:
        """Verify that ordinary rooms contribute no dynamic clue text."""
        engine = make_engine(mock_describe=False)

        self.assertEqual(engine._current_room_clue(engine.rooms["lobby"]), "")

    def test_describe_current_room_skips_unknown_room_ids(self) -> None:
        """Verify that missing room IDs produce no room view or rendered output."""
        engine = make_engine(mock_describe=False)
        engine.state.current_room_id = "missing_room"
        output = io.StringIO()

        with redirect_stdout(output):
            engine.describe_current_room()

        self.assertIsNone(engine._current_room_view())
        self.assertEqual(output.getvalue(), "")

    def test_intro_helpers_render_banner_and_story_copy(self) -> None:
        """Verify that intro helper methods expose the configured banner and hook text."""
        engine = make_engine(mock_describe=False)

        lines = engine._intro_banner_lines()
        output = io.StringIO()
        with redirect_stdout(output):
            engine._print_intro()

        self.assertEqual(lines[-1], UI["intro"]["title"])
        self.assertIn("=" * 60, output.getvalue())
        self.assertIn(UI["intro"]["opening"], output.getvalue())
        self.assertIn(UI["intro"]["teacher"], output.getvalue())

    def test_describe_current_room_renders_shared_room_view_content(self) -> None:
        """Verify that describe_current_room() prints room name, clue, exits, items, and time."""
        engine, _room = make_intersection_engine()

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            engine.describe_current_room()

        output = buffer.getvalue()
        self.assertIn("[ 4-Way Intersection ]", output)
        self.assertIn("right hallway", output)
        self.assertIn("Exits: left, right", output)
        self.assertIn("You see: exam poster", output)
        self.assertIn("Time remaining: 2:05", output)

    def test_run_processes_events_and_quit_command_before_handling_end(self) -> None:
        """Verify that run() prints events, dispatches one command, and ends cleanly on quit."""
        engine = make_engine(mock_describe=False)
        output = io.StringIO()

        with (
            patch.object(engine, "_print_intro") as print_intro_mock,
            patch.object(engine, "describe_current_room") as describe_mock,
            patch.object(engine, "_handle_end") as handle_end_mock,
            patch.object(engine.state, "tick") as tick_mock,
            patch.object(
                engine.event_queue,
                "tick",
                return_value=["The lights flicker."],
            ),
            patch("builtins.input", return_value="quit"),
            redirect_stdout(output),
        ):
            engine.run()

        print_intro_mock.assert_called_once_with()
        describe_mock.assert_called_once_with()
        tick_mock.assert_called_once_with()
        handle_end_mock.assert_called_once_with()
        self.assertTrue(engine.state.quit)
        self.assertIn("The lights flicker.", output.getvalue())
        self.assertIn("Game over.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
