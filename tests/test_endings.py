"""Integration tests for game-ending selection and output.

Verifies that the win, timeout, and quit endings are printed correctly
for both the plain-text and curses UI layers.
"""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from game.engine.engine import GameEngine, UI
from tests.helpers import make_engine


class EngineEndingTest(unittest.TestCase):
    """Verify ending selection for win, weird ending, loss, and quit."""

    def test_handle_end_uses_correct_ending_variant(self) -> None:
        """Verify that _handle_end() selects won_early, won, or lost based on state flags and time."""
        cases = [
            (True, False, 300, "TOMORROW"),
            (True, False, 240, "already in progress"),
            (False, False, 0, "TIME'S UP."),
        ]

        for won, quit_game, time_remaining, expected in cases:
            with self.subTest(won=won, quit=quit_game, time_remaining=time_remaining):
                engine = make_engine(time_remaining=time_remaining)
                engine.state.won = won
                engine.state.quit = quit_game
                output = io.StringIO()

                with (
                    patch("builtins.input", return_value="x") as input_mock,
                    redirect_stdout(output),
                ):
                    GameEngine._handle_end(engine)

                self.assertIn("=" * 60, output.getvalue())
                self.assertIn(expected, output.getvalue())
                input_mock.assert_called_once_with(
                    f"\n{UI['end']['press_enter_to_replay']} "
                )
                self.assertFalse(engine.state.replay_requested)

    def test_handle_end_prints_nothing_after_quit(self) -> None:
        """Verify that _handle_end() produces no output when the player quit the game."""
        engine = make_engine()
        engine.state.quit = True
        output = io.StringIO()

        with redirect_stdout(output):
            GameEngine._handle_end(engine)

        self.assertEqual(output.getvalue(), "")

    def test_handle_end_sets_replay_requested_when_enter_is_pressed(self) -> None:
        """Verify that the plain-text ending prompt requests replay on blank input."""
        engine = make_engine(time_remaining=240)
        engine.state.won = True
        output = io.StringIO()

        with (
            patch("builtins.input", return_value="") as input_mock,
            redirect_stdout(output),
        ):
            GameEngine._handle_end(engine)

        self.assertTrue(engine.state.replay_requested)
        input_mock.assert_called_once_with(f"\n{UI['end']['press_enter_to_replay']} ")


if __name__ == "__main__":
    unittest.main()
