"""Unit tests for bathroom, intersection, janitor, and puzzle-domain helpers.

Tests the public helper surfaces from :mod:`game.puzzles.bathroom`,
:mod:`game.intersection`, :mod:`game.janitor`, and :mod:`game.puzzle` in
isolation using a fresh world and state.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from game import load_yaml_data
from game.puzzles.bathroom import (
    apply_soap,
    bathroom_exit_block_message,
    rinse_hands,
    step2_roll,
    stop_sink,
)
from game.puzzles.bathroom_view import (
    bathroom_mirror_text,
    bathroom_sink_text,
    bathroom_status_text,
    step2_mirror_text,
)
from game.puzzles.intersection import step1_clue_text, step1_read_text, step1_roll
from game.puzzles.janitor import janitor_text, step3_roll
from game.puzzles.puzzle import (
    clue_direction_matches,
)
from game.state import GameState
from tests.helpers import make_room_context

_CMD = load_yaml_data("commands.yaml")["responses"]


class BathroomHelpersTest(unittest.TestCase):
    """Verify shared bathroom puzzle helpers used by command handlers."""

    def setUp(self) -> None:
        """Create a fresh bathroom room and bathroom-scoped game state for each test."""
        self.bathroom, self.state = make_room_context("bathroom")

    def test_bathroom_exit_block_message_tracks_phase_and_cleanliness(self) -> None:
        """Verify that bathroom_exit_block_message returns phase-appropriate messages or None when clean."""
        self.assertEqual(
            bathroom_exit_block_message(self.bathroom, self.state, _CMD["move"]),
            _CMD["move"]["hands_not_washed"],
        )

        self.bathroom.attributes["wash_phase"] = 1
        self.assertEqual(
            bathroom_exit_block_message(self.bathroom, self.state, _CMD["move"]),
            _CMD["move"]["hands_still_soapy"],
        )

        self.bathroom.attributes.update({"wash_phase": 2, "sink_running": True})
        self.assertEqual(
            bathroom_exit_block_message(self.bathroom, self.state, _CMD["move"]),
            _CMD["move"]["hands_still_soapy"],
        )

        self.state.set_flag("step2_hands_washed")
        self.assertIsNone(
            bathroom_exit_block_message(self.bathroom, self.state, _CMD["move"])
        )

    def test_bathroom_mirror_and_sink_text_reflect_clean_state(self) -> None:
        """Verify that mirror text stays fogged and sink text tracks running state until hands are clean."""
        self.state.active_clues["step2_mirror_dir"] = "left"

        self.assertEqual(
            bathroom_mirror_text(self.state, _CMD["look"]["mirror_fogged"]),
            _CMD["look"]["mirror_fogged"],
        )
        self.assertEqual(
            bathroom_sink_text(self.bathroom, self.state, _CMD["look"]),
            _CMD["look"]["sink_off"],
        )

        self.bathroom.attributes["sink_running"] = True
        self.assertEqual(
            bathroom_sink_text(self.bathroom, self.state, _CMD["look"]),
            _CMD["look"]["sink_running_rinse"],
        )

        self.state.set_flag("step2_hands_washed")
        self.assertIn(
            "GO LEFT",
            bathroom_mirror_text(self.state, _CMD["look"]["mirror_fogged"]),
        )
        self.assertEqual(
            bathroom_sink_text(self.bathroom, self.state, _CMD["look"]),
            _CMD["look"]["sink_clean"],
        )

    def test_bathroom_status_text_tracks_phase_and_cleanliness(self) -> None:
        """Verify that bathroom_status_text reflects soap, rinse, and clean-state phases."""
        self.bathroom.attributes["sink_running"] = True

        self.assertEqual(
            bathroom_status_text(self.bathroom, self.state, _CMD["bathroom_status"]),
            _CMD["bathroom_status"]["soap_needed"],
        )

        self.bathroom.attributes["soap_applied"] = True
        self.assertEqual(
            bathroom_status_text(self.bathroom, self.state, _CMD["bathroom_status"]),
            _CMD["bathroom_status"]["soapy"],
        )

        self.bathroom.attributes["wash_phase"] = 1
        self.bathroom.attributes["sink_running"] = False
        self.assertEqual(
            bathroom_status_text(self.bathroom, self.state, _CMD["bathroom_status"]),
            _CMD["bathroom_status"]["water_cut"],
        )

        self.state.set_flag("step2_hands_washed")
        self.assertEqual(
            bathroom_status_text(self.bathroom, self.state, _CMD["bathroom_status"]),
            _CMD["bathroom_status"]["clean"],
        )

    def test_bathroom_read_only_helpers_ignore_non_bathroom_rooms(self) -> None:
        """Verify that bathroom-only read-only helpers short-circuit outside the bathroom."""
        lobby, lobby_state = make_room_context("lobby")

        self.assertIsNone(bathroom_exit_block_message(lobby, lobby_state, _CMD["move"]))
        self.assertEqual(
            bathroom_status_text(lobby, lobby_state, _CMD["bathroom_status"]),
            "",
        )

    def test_bathroom_sink_and_status_share_running_phase_mapping(self) -> None:
        """Verify that running-sink phases stay aligned between sink and ambient status text."""
        self.bathroom.attributes.update({"sink_running": True, "wash_phase": 2})

        self.assertEqual(
            bathroom_sink_text(self.bathroom, self.state, _CMD["look"]),
            _CMD["look"]["sink_running_rinse"],
        )
        self.assertEqual(
            bathroom_status_text(self.bathroom, self.state, _CMD["bathroom_status"]),
            _CMD["bathroom_status"]["water_back"],
        )

        self.bathroom.attributes["wash_phase"] = 3

        self.assertEqual(
            bathroom_sink_text(self.bathroom, self.state, _CMD["look"]),
            _CMD["look"]["sink_running_stop"],
        )
        self.assertEqual(
            bathroom_status_text(self.bathroom, self.state, _CMD["bathroom_status"]),
            _CMD["bathroom_status"]["final_rinse"],
        )

    def test_bathroom_action_helpers_advance_puzzle_state(self) -> None:
        """Verify that apply_soap, rinse_hands, and stop_sink advance wash_phase through the full sequence."""
        self.assertEqual(
            apply_soap(self.bathroom, self.state, _CMD["soap"]),
            _CMD["soap"]["applied"],
        )
        self.assertTrue(self.bathroom.attributes["soap_applied"])

        first_rinse = rinse_hands(self.bathroom, self.state, _CMD["rinse"])
        self.assertEqual(first_rinse, _CMD["rinse"]["phase_0"])
        self.assertEqual(self.bathroom.attributes["wash_phase"], 1)
        self.assertFalse(self.bathroom.attributes["sink_running"])

        reset = stop_sink(self.bathroom, self.state, _CMD["stop"])
        self.assertEqual(reset, _CMD["stop"]["phase_1"])
        self.assertEqual(self.bathroom.attributes["wash_phase"], 2)
        self.assertTrue(self.bathroom.attributes["sink_running"])

        second_rinse = rinse_hands(self.bathroom, self.state, _CMD["rinse"])
        self.assertEqual(second_rinse, _CMD["rinse"]["phase_2"])
        self.assertEqual(self.bathroom.attributes["wash_phase"], 3)

        finish = stop_sink(self.bathroom, self.state, _CMD["stop"])
        self.assertEqual(finish, _CMD["stop"]["phase_3"])
        self.assertEqual(self.bathroom.attributes["wash_phase"], 4)
        self.assertTrue(self.state.has_flag("step2_hands_washed"))
        self.assertTrue(self.state.has_flag("step2_mirror_clue_visible"))

    def test_bathroom_action_helpers_short_circuit_when_hands_are_clean(self) -> None:
        """Verify that soap, rinse, and stop all return already_clean responses once hands are washed."""
        self.bathroom.attributes.update(
            {
                "soap_applied": False,
                "wash_phase": 2,
                "sink_running": True,
            }
        )
        self.state.set_flag("step2_hands_washed")

        self.assertEqual(
            apply_soap(self.bathroom, self.state, _CMD["soap"]),
            _CMD["soap"]["already_clean"],
        )
        self.assertEqual(
            rinse_hands(self.bathroom, self.state, _CMD["rinse"]),
            _CMD["rinse"]["already_clean"],
        )
        self.assertEqual(
            stop_sink(self.bathroom, self.state, _CMD["stop"]),
            _CMD["stop"]["already_clean"],
        )
        self.assertFalse(self.bathroom.attributes["soap_applied"])
        self.assertEqual(self.bathroom.attributes["wash_phase"], 2)
        self.assertTrue(self.bathroom.attributes["sink_running"])

    def test_rinse_hands_escalates_wrong_phase_responses(self) -> None:
        """Verify that repeated Phase 1 rinse attempts advance through the escalating warning texts."""
        self.bathroom.attributes.update(
            {
                "soap_applied": True,
                "wash_phase": 1,
                "sink_running": False,
            }
        )

        self.assertEqual(
            rinse_hands(self.bathroom, self.state, _CMD["rinse"]),
            _CMD["rinse"]["phase_1_wrong"],
        )
        self.assertEqual(
            rinse_hands(self.bathroom, self.state, _CMD["rinse"]),
            _CMD["rinse"]["phase_1_wrong_2"],
        )
        self.assertEqual(
            rinse_hands(self.bathroom, self.state, _CMD["rinse"]),
            _CMD["rinse"]["phase_1_wrong_3"],
        )
        self.assertEqual(self.bathroom.attributes["rinse_phase1_attempts"], 3)

    def test_bathroom_response_text_avoids_literal_unicode_escape_sequences(
        self,
    ) -> None:
        """Verify that bathroom response strings render punctuation directly instead of raw escapes."""
        self.assertNotIn("\\u2014", _CMD["stop"]["phase_1"])
        self.assertNotIn("\\u2014", _CMD["bathroom_status"]["water_back"])
        self.assertNotIn("\\u2192", _CMD["rinse"]["phase_1_wrong_3"])
        self.assertIn(
            "RINSE -> STOP -> RINSE -> STOP", _CMD["rinse"]["phase_1_wrong_3"]
        )

    def test_bathroom_action_helpers_cover_non_transition_fallbacks(self) -> None:
        """Verify that stop and soap still return the correct non-transition fallback responses."""
        self.assertEqual(
            stop_sink(self.bathroom, self.state, _CMD["stop"]),
            _CMD["stop"]["phase_0"],
        )

        self.bathroom.attributes["wash_phase"] = 2
        self.assertEqual(
            apply_soap(self.bathroom, self.state, _CMD["soap"]),
            _CMD["soap"]["wrong_phase"],
        )

        self.bathroom.attributes.update({"wash_phase": 0, "soap_applied": True})
        self.assertEqual(
            apply_soap(self.bathroom, self.state, _CMD["soap"]),
            _CMD["soap"]["already_applied"],
        )


class JanitorHelpersTest(unittest.TestCase):
    """Verify shared janitor clue formatting helpers."""

    def test_janitor_text_reveals_more_lines_as_time_runs_low(self) -> None:
        """Verify that janitor_text exposes more chorus lines progressively as time decreases."""
        state = GameState(current_room_id="hallway_janitor", time_remaining=600)
        state.active_clues["step3_song_chorus"] = (
            "Take the left hall\nTake it again\nOne more line"
        )

        early = janitor_text(state, _CMD["ambient"]["janitor_hint_prefix"])
        self.assertIn("Take the left hall", early)
        self.assertNotIn("Take it again", early)

        state.time_remaining = 240
        mid = janitor_text(state, _CMD["ambient"]["janitor_hint_prefix"])
        self.assertIn("Take the left hall", mid)
        self.assertIn("Take it again", mid)
        self.assertNotIn("One more line", mid)

        state.time_remaining = 120
        late = janitor_text(state, _CMD["ambient"]["janitor_hint_prefix"])
        self.assertIn("One more line", late)

    def test_janitor_text_formats_full_chorus_for_listen(self) -> None:
        """Verify that janitor_text returns the full indented chorus when full_chorus is set."""
        state = GameState(current_room_id="hallway_janitor")
        state.active_clues["step3_song_chorus"] = "Take the left hall\nTake it again"

        heard = janitor_text(
            state,
            _CMD["listen"]["janitor_prefix"],
            full_chorus=True,
        )

        self.assertIn("The janitor is humming.", heard)
        self.assertIn("\n  Take the left hall\n  Take it again", heard)


class PuzzleHelpersTest(unittest.TestCase):
    """Verify clue generation and clue checks."""

    def test_step1_roll_records_direction_and_clue_type(self) -> None:
        """Verify that step1_roll stores the correct direction and clue type in active_clues."""
        state = GameState(current_room_id="intersection_4way")

        with patch("game.puzzles.puzzle.random.choice", side_effect=["left", "sign"]):
            step1_roll(state)

        self.assertEqual(state.active_clues["step1_correct_dir"], "left")
        self.assertEqual(state.active_clues["step1_clue_type"], "sign")

    def test_step1_roll_excludes_shadow_for_forward_direction(self) -> None:
        """Verify that the shadow clue is not eligible when Step 1 points straight ahead."""
        state = GameState(current_room_id="intersection_4way")
        choice_calls: list[tuple[str, ...]] = []

        def choose(options: tuple[str, ...] | list[str]) -> str:
            """Record each choice pool and force a forward-then-light roll order."""
            """Record each choice pool and force a forward-then-light roll order."""
            option_tuple: tuple[str, ...] = tuple(options)
            choice_calls.append(option_tuple)
            return "forward" if len(choice_calls) == 1 else "light"

        with patch("game.puzzles.puzzle.random.choice", side_effect=choose):
            step1_roll(state)

        self.assertEqual(state.active_clues["step1_correct_dir"], "forward")
        self.assertEqual(state.active_clues["step1_clue_type"], "light")
        self.assertEqual(choice_calls[1], ("light", "sign"))

    def test_step1_clue_text_uses_template_and_correct_direction(self) -> None:
        """Verify that the Step 1 light clue points at the correct hallway."""
        state = GameState(current_room_id="intersection_4way")
        state.active_clues.update(
            {
                "step1_correct_dir": "left",
                "step1_clue_type": "light",
            }
        )

        clue = step1_clue_text(state)

        self.assertIn("left hallway", clue)
        self.assertNotIn("right hallway", clue)
        self.assertTrue(clue_direction_matches("left", state, "step1_correct_dir"))
        self.assertFalse(clue_direction_matches("forward", state, "step1_correct_dir"))

    def test_step1_read_text_only_exposes_flyer_when_sign_clue_is_active(self) -> None:
        """Verify that flyer reads reuse the Step 1 sign clue and otherwise fall back to not-here."""
        state = GameState(current_room_id="intersection_4way")
        not_here = "There is no '{target}' here to read."

        self.assertEqual(
            step1_read_text(state, "flyer", not_here), not_here.format(target="flyer")
        )

        state.active_clues.update(
            {
                "step1_correct_dir": "forward",
                "step1_clue_type": "sign",
            }
        )

        clue = step1_read_text(state, "flyer", not_here)

        self.assertIn("CS CLUB BAKE SALE", clue)
        self.assertIn("pointing forward", clue)

    def test_step2_roll_and_mirror_text_encode_direction(self) -> None:
        """Verify that step2_roll seeds the mirror direction and step2_mirror_text encodes it in reverse."""
        state = GameState(current_room_id="bathroom")

        def seed_step2_direction(seed_state: GameState, clue_key: str) -> str:
            """Seed the mirror clue direction without using random selection."""
            seed_state.active_clues[clue_key] = "right"
            return "right"

        with patch(
            "game.puzzles.bathroom.roll_turn_direction",
            side_effect=seed_step2_direction,
        ):
            step2_roll(state)

        clue = step2_mirror_text(state)

        self.assertEqual(state.active_clues["step2_mirror_dir"], "right")
        self.assertIn('"THGIR OG"', clue)
        self.assertIn("GO RIGHT", clue)

    def test_step3_roll_uses_direction_specific_song_pool(self) -> None:
        """Verify that step3_roll picks a song from the correct pool and stores direction and chorus."""
        state = GameState(current_room_id="hallway_janitor")

        def seed_step3_direction(seed_state: GameState, clue_key: str) -> str:
            """Seed the janitor clue direction without using random selection."""
            seed_state.active_clues[clue_key] = "left"
            return "left"

        with (
            patch(
                "game.puzzles.janitor.roll_turn_direction",
                side_effect=seed_step3_direction,
            ),
            patch(
                "game.janitor.random.choice",
                return_value=("Turn Left Anthem", "Step to the left"),
            ),
        ):
            step3_roll(state)

        self.assertEqual(state.active_clues["step3_correct_dir"], "left")
        self.assertEqual(state.active_clues["step3_song_chorus"], "Step to the left")
        self.assertTrue(clue_direction_matches("left", state, "step3_correct_dir"))
        self.assertFalse(clue_direction_matches("right", state, "step3_correct_dir"))


if __name__ == "__main__":
    unittest.main()
