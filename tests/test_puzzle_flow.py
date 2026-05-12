"""Integration tests for navigation and puzzle progression.

Covers the full directional-movement pipeline including puzzle-step
transitions, wrong-way routing, and the victory state reached upon
entering Room 314.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from game.state import GameState
from game.world import FLAVOR_ROOM_POOL
from tests.helpers import describe_mock, dispatch, make_engine


class MovementAndPuzzleFlowTest(unittest.TestCase):
    """Verify navigation, puzzle steps, and victory state changes."""

    def test_movement_distinguishes_missing_and_blocked_exits(self) -> None:
        """Verify that missing exits and puzzle-blocked exits each produce distinct messages."""
        engine = make_engine()

        self.assertEqual(dispatch(engine, "right"), "You can't go that way.")
        self.assertEqual(
            dispatch(engine, "forward"),
            "There isn't anyone around, but the hallway is thoroughly blocked off.",
        )
        self.assertEqual(
            dispatch(engine, "back"),
            "You can't run from your problems, you need to take your final.",
        )
        self.assertEqual(engine.state.current_room_id, "lobby")

    def test_entering_intersection_4way_rolls_and_wires_routes(self) -> None:
        """Verify that entering the 4-way wires both the correct and wrong detour chains."""
        engine = make_engine(start_room="hallway_approach")

        def seed_step1(state: GameState) -> None:
            """Seed Step 1 with a stable direction and clue type for this route test."""
            state.active_clues["step1_correct_dir"] = "left"
            state.active_clues["step1_clue_type"] = "sign"

        with (
            patch("game.commands.player_movement.step1_roll", side_effect=seed_step1),
            patch("game.commands.player_movement.random.randint", side_effect=[1, 2]),
            patch(
                "game.commands.player_movement.random.sample",
                side_effect=[
                    ["flavor_copy_room"],
                    ["flavor_stairwell", "flavor_study_lounge"],
                ],
            ),
        ):
            result = dispatch(engine, "forward")

        self.assertEqual(result, "")
        self.assertEqual(engine.state.current_room_id, "intersection_4way")
        self.assertEqual(
            engine.rooms["intersection_4way"].exits["left"], "flavor_copy_room"
        )
        self.assertEqual(
            engine.rooms["intersection_4way"].exits["forward"], "flavor_stairwell"
        )
        self.assertEqual(
            engine.rooms["intersection_4way"].exits["right"], "flavor_stairwell"
        )
        self.assertEqual(
            engine.rooms["flavor_copy_room"].exits["forward"], "intersection_3way"
        )
        self.assertEqual(
            engine.rooms["flavor_copy_room"].exits["back"], "intersection_3way"
        )
        self.assertEqual(
            engine.rooms["flavor_stairwell"].exits["forward"], "flavor_study_lounge"
        )
        self.assertEqual(
            engine.rooms["flavor_stairwell"].exits["back"], "flavor_study_lounge"
        )
        self.assertEqual(
            engine.rooms["flavor_study_lounge"].exits["forward"], "intersection_4way"
        )
        self.assertEqual(
            engine.rooms["flavor_study_lounge"].exits["back"], "intersection_4way"
        )
        self.assertTrue(engine.state.has_flag("step1_seen_intersection"))
        self.assertFalse(engine.state.has_flag("step1_returned_to_intersection"))
        describe_mock(engine).assert_called_once()

    def test_entering_hallway_approach_wires_both_exits_into_detour_chain(self) -> None:
        """Verify that the lobby-to-4-way hallway rewires both directions through a short detour."""
        engine = make_engine()

        with (
            patch("game.commands.player_movement.random.randint", return_value=2),
            patch(
                "game.commands.player_movement.random.sample",
                return_value=["flavor_copy_room", "flavor_stairwell"],
            ),
        ):
            result = dispatch(engine, "left")

        hallway = engine.rooms["hallway_approach"]
        self.assertEqual(result, "")
        self.assertEqual(engine.state.current_room_id, "hallway_approach")
        self.assertEqual(hallway.exits["forward"], "flavor_copy_room")
        self.assertEqual(hallway.exits["back"], "flavor_copy_room")
        self.assertEqual(
            engine.rooms["flavor_copy_room"].exits["forward"], "flavor_stairwell"
        )
        self.assertEqual(
            engine.rooms["flavor_copy_room"].exits["back"], "flavor_stairwell"
        )
        self.assertEqual(
            engine.rooms["flavor_stairwell"].exits["forward"], "intersection_4way"
        )
        self.assertEqual(
            engine.rooms["flavor_stairwell"].exits["back"], "intersection_4way"
        )
        describe_mock(engine).assert_called_once()

    def test_flavor_detour_rooms_accept_back_as_another_step_toward_intersection(
        self,
    ) -> None:
        """Verify that BACK advances through interstitial detour rooms just like FORWARD."""
        engine = make_engine()

        with (
            patch("game.commands.player_movement.random.randint", return_value=2),
            patch(
                "game.commands.player_movement.random.sample",
                return_value=["flavor_copy_room", "flavor_stairwell"],
            ),
        ):
            dispatch(engine, "left")
            dispatch(engine, "back")
            result = dispatch(engine, "back")

        self.assertEqual(result, "")
        self.assertEqual(engine.state.current_room_id, "flavor_stairwell")

    def test_returning_to_intersection_marks_reset_state(self) -> None:
        """Verify that re-entering the 4-way sets the return flag used by the reset line."""
        engine = make_engine(start_room="hallway_approach")

        step1_rolls = iter(
            [
                ("left", "sign"),
                ("right", "light"),
            ]
        )

        def seed_step1(state: GameState) -> None:
            """Advance through a predetermined Step 1 clue sequence on each revisit."""
            correct_dir, clue_type = next(step1_rolls)
            state.active_clues["step1_correct_dir"] = correct_dir
            state.active_clues["step1_clue_type"] = clue_type

        with (
            patch("game.commands.player_movement.step1_roll", side_effect=seed_step1),
            patch(
                "game.commands.player_movement.random.randint",
                side_effect=[1, 2, 1, 2],
            ),
            patch(
                "game.commands.player_movement.random.sample",
                side_effect=[
                    ["flavor_copy_room"],
                    ["flavor_stairwell", "flavor_study_lounge"],
                    ["flavor_classroom_195"],
                    ["flavor_faculty_office", "flavor_water_fountain"],
                ],
            ),
        ):
            dispatch(engine, "forward")
            dispatch(engine, "forward")
            dispatch(engine, "forward")
            dispatch(engine, "forward")

        self.assertEqual(engine.state.current_room_id, "intersection_4way")
        self.assertTrue(engine.state.has_flag("step1_seen_intersection"))
        self.assertTrue(engine.state.has_flag("step1_returned_to_intersection"))
        self.assertEqual(engine.state.used_interstitial_room_ids, set(FLAVOR_ROOM_POOL))

    def test_detours_only_recycle_flavor_rooms_after_unused_pool_runs_out(self) -> None:
        """Verify that detours consume the last unused room before reusing older ones."""
        engine = make_engine(start_room="lobby")
        engine.state.used_interstitial_room_ids.update(
            {
                "flavor_copy_room",
                "flavor_faculty_office",
                "flavor_study_lounge",
                "flavor_stairwell",
                "flavor_classroom_195",
            }
        )

        with (
            patch("game.commands.player_movement.random.randint", return_value=2),
            patch(
                "game.commands.player_movement.random.sample",
                side_effect=[
                    ["flavor_water_fountain"],
                    ["flavor_copy_room"],
                ],
            ),
        ):
            result = dispatch(engine, "left")

        self.assertEqual(result, "")
        self.assertEqual(engine.state.current_room_id, "hallway_approach")
        self.assertEqual(
            engine.rooms["hallway_approach"].exits["forward"],
            "flavor_water_fountain",
        )
        self.assertEqual(
            engine.rooms["flavor_water_fountain"].exits["forward"],
            "flavor_copy_room",
        )
        self.assertEqual(
            engine.rooms["flavor_copy_room"].exits["forward"],
            "intersection_4way",
        )
        self.assertEqual(engine.state.used_interstitial_room_ids, set(FLAVOR_ROOM_POOL))

    def test_wrong_direction_at_4way_loops_player_through_flavor_room(self) -> None:
        """Verify that taking a wrong turn at the 4-way routes through a flavor room and increments wrong_turns."""
        engine = make_engine(start_room="intersection_4way")
        engine.state.active_clues["step1_correct_dir"] = "left"
        engine.rooms["intersection_4way"].exits.update(
            {
                "left": "intersection_3way",
                "forward": "flavor_copy_room",
                "right": "flavor_stairwell",
            }
        )

        result = dispatch(engine, "forward")

        self.assertIn("Something feels wrong.", result)
        self.assertEqual(engine.state.current_room_id, "flavor_copy_room")
        self.assertEqual(engine.state.wrong_turns, 1)
        self.assertTrue(engine.state.has_flag("step1_wrong_way"))

    def test_correct_direction_at_4way_advances_to_next_puzzle_step(self) -> None:
        """Verify that the correct 4-way turn advances puzzle state before the next junction."""
        engine = make_engine(start_room="intersection_4way")
        engine.state.active_clues["step1_correct_dir"] = "left"
        engine.rooms["intersection_4way"].exits["left"] = "flavor_copy_room"
        engine.rooms["flavor_copy_room"].exits["forward"] = "intersection_3way"
        engine.rooms["flavor_copy_room"].exits["back"] = "intersection_3way"

        result = dispatch(engine, "left")

        self.assertEqual(result, "")
        self.assertEqual(engine.state.current_room_id, "flavor_copy_room")
        self.assertEqual(engine.state.puzzle_step, 1)
        self.assertTrue(engine.state.has_flag("step1_solved"))

    def test_entering_three_way_wires_visible_side_halls_into_a_detour_chain(
        self,
    ) -> None:
        """Verify that the first 3-way junction exposes left/right side halls that loop back."""
        engine = make_engine(start_room="flavor_copy_room")
        engine.rooms["flavor_copy_room"].exits["forward"] = "intersection_3way"

        with (
            patch("game.commands.player_movement.random.randint", return_value=2),
            patch(
                "game.commands.player_movement.random.sample",
                return_value=["flavor_study_lounge", "flavor_water_fountain"],
            ),
        ):
            result = dispatch(engine, "forward")

        self.assertEqual(result, "")
        self.assertEqual(engine.state.current_room_id, "intersection_3way")
        self.assertEqual(engine.rooms["intersection_3way"].exits["forward"], "bathroom")
        self.assertEqual(
            engine.rooms["intersection_3way"].exits["back"], "intersection_4way"
        )
        self.assertEqual(
            engine.rooms["intersection_3way"].exits["left"], "flavor_study_lounge"
        )
        self.assertEqual(
            engine.rooms["intersection_3way"].exits["right"], "flavor_study_lounge"
        )
        self.assertEqual(
            engine.rooms["flavor_study_lounge"].exits["forward"],
            "flavor_water_fountain",
        )
        self.assertEqual(
            engine.rooms["flavor_study_lounge"].exits["back"],
            "flavor_water_fountain",
        )
        self.assertEqual(
            engine.rooms["flavor_water_fountain"].exits["forward"],
            "intersection_3way",
        )
        self.assertEqual(
            engine.rooms["flavor_water_fountain"].exits["back"],
            "intersection_3way",
        )

    def test_bathroom_entry_rolls_mirror_direction_and_starts_sink(self) -> None:
        """Verify that entering the bathroom runs step2_roll and activates the sink."""
        engine = make_engine(start_room="intersection_3way")

        def seed_step2(state: GameState) -> None:
            """Seed the bathroom mirror clue without relying on random direction selection."""
            state.active_clues["step2_mirror_dir"] = "right"

        with patch("game.commands.player_movement.step2_roll", side_effect=seed_step2):
            result = dispatch(engine, "forward")

        self.assertEqual(result, "")
        self.assertEqual(engine.state.current_room_id, "bathroom")
        self.assertTrue(engine.state.has_flag("step2_rolled"))
        self.assertEqual(engine.state.active_clues["step2_mirror_dir"], "right")
        self.assertTrue(engine.rooms["bathroom"].attributes["sink_running"])

    def test_initial_three_way_backtracks_directly_to_four_way(self) -> None:
        """Verify that the first 3-way junction still lets the player go straight back to the 4-way."""
        engine = make_engine(start_room="intersection_3way")

        result = dispatch(engine, "back")

        self.assertEqual(result, "")
        self.assertEqual(engine.state.current_room_id, "intersection_4way")

    def test_bathroom_exit_is_blocked_until_hands_are_clean(self) -> None:
        """Verify that moving back from the bathroom is blocked at each wash phase until complete."""
        engine = make_engine(start_room="bathroom")
        bathroom = engine.rooms["bathroom"]

        self.assertEqual(
            dispatch(engine, "back"), "You feel like you should wash your hands."
        )

        bathroom.attributes["wash_phase"] = 1
        self.assertEqual(
            dispatch(engine, "back"),
            "Your hands are still soapy. You should rinse them off first.",
        )
        self.assertEqual(engine.state.current_room_id, "bathroom")

    def test_bathroom_puzzle_requires_soap_and_reveals_mirror_clue_when_completed(
        self,
    ) -> None:
        """Verify the full handwashing sequence: soap → rinse → stop → rinse → stop reveals the mirror clue."""
        engine = make_engine(start_room="bathroom")
        bathroom = engine.rooms["bathroom"]
        bathroom.attributes["sink_running"] = True
        engine.state.active_clues["step2_mirror_dir"] = "left"

        self.assertIn("use soap first", dispatch(engine, "rinse", "hands"))
        self.assertIn("lather up", dispatch(engine, "soap", "hands"))

        first_rinse = dispatch(engine, "rinse", "hands")
        self.assertIn("cuts off", first_rinse)
        self.assertEqual(bathroom.attributes["wash_phase"], 1)
        self.assertFalse(bathroom.attributes["sink_running"])

        self.assertIn("Pull your hands back first", dispatch(engine, "rinse", "hands"))

        reset = dispatch(engine, "stop")
        self.assertIn("water comes back on", reset)
        self.assertEqual(bathroom.attributes["wash_phase"], 2)
        self.assertTrue(bathroom.attributes["sink_running"])
        self.assertEqual(bathroom.attributes["rinse_phase1_attempts"], 0)

        second_rinse = dispatch(engine, "rinse", "hands")
        self.assertIn("water stays running", second_rinse)
        self.assertEqual(bathroom.attributes["wash_phase"], 3)

        finish = dispatch(engine, "stop")
        self.assertIn("mirror has cleared", finish)
        self.assertEqual(bathroom.attributes["wash_phase"], 4)
        self.assertFalse(bathroom.attributes["sink_running"])
        self.assertTrue(engine.state.has_flag("step2_hands_washed"))
        self.assertTrue(engine.state.has_flag("step2_mirror_clue_visible"))
        self.assertIn("GO LEFT", dispatch(engine, "read", "mirror"))

    def test_bathroom_look_and_read_route_targeted_room_helpers(self) -> None:
        """Verify that bathroom look/read targets dispatch to their room-target handlers."""
        engine = make_engine(start_room="bathroom")
        bathroom = engine.rooms["bathroom"]
        bathroom.attributes["sink_running"] = True
        engine.state.active_clues["step2_mirror_dir"] = "left"

        mirror_result = dispatch(engine, "look", "mirror")
        sink_result = dispatch(engine, "look", "sink")
        read_result = dispatch(engine, "read", "mirror")

        self.assertIn("fogged", mirror_result)
        self.assertIn("Try: RINSE HANDS", sink_result)
        self.assertIn("fogged", read_result)
        describe_mock(engine).assert_not_called()

    def test_exiting_bathroom_wires_exit_node_from_mirror_direction(self) -> None:
        """Verify that exiting the bathroom rewires the intersection_3way_exit based on the mirror direction."""
        engine = make_engine(start_room="bathroom")
        engine.state.set_flag("step2_hands_washed")
        engine.state.active_clues["step2_mirror_dir"] = "left"

        with (
            patch("game.commands.player_movement.random.randint", return_value=2),
            patch(
                "game.commands.player_movement.random.sample",
                return_value=["flavor_stairwell", "flavor_study_lounge"],
            ),
        ):
            result = dispatch(engine, "back")

        self.assertEqual(result, "")
        self.assertEqual(engine.state.current_room_id, "intersection_3way_exit")
        self.assertEqual(
            engine.rooms["intersection_3way_exit"].exits["left"], "flavor_stairwell"
        )
        self.assertEqual(
            engine.rooms["intersection_3way_exit"].exits["forward"], "flavor_copy_room"
        )
        self.assertEqual(
            engine.rooms["intersection_3way_exit"].exits["right"], "flavor_copy_room"
        )
        self.assertEqual(
            engine.rooms["flavor_stairwell"].exits["forward"], "flavor_study_lounge"
        )
        self.assertEqual(
            engine.rooms["flavor_stairwell"].exits["back"], "flavor_study_lounge"
        )
        self.assertEqual(
            engine.rooms["flavor_study_lounge"].exits["forward"], "hallway_janitor"
        )
        self.assertEqual(
            engine.rooms["flavor_study_lounge"].exits["back"], "hallway_janitor"
        )
        self.assertEqual(
            engine.rooms["flavor_copy_room"].exits["forward"], "intersection_3way_exit"
        )
        self.assertEqual(
            engine.rooms["flavor_copy_room"].exits["back"], "intersection_3way_exit"
        )

    def test_entering_janitor_hallway_rolls_song_and_wires_wrong_way_return(
        self,
    ) -> None:
        """Verify that entering janitor wires a final-stretch chain and the wrong-way loop."""
        engine = make_engine(start_room="intersection_3way_exit")
        engine.rooms["intersection_3way_exit"].exits["right"] = "hallway_janitor"

        def seed_step3(state: GameState) -> None:
            """Seed the janitor clue direction and chorus for a deterministic hallway setup."""
            state.active_clues["step3_correct_dir"] = "left"
            state.active_clues["step3_song_chorus"] = "Take the left hall"

        with (
            patch("game.commands.player_movement.step3_roll", side_effect=seed_step3),
            patch("game.commands.player_movement.random.randint", return_value=1),
            patch(
                "game.commands.player_movement.random.sample",
                return_value=["flavor_stairwell"],
            ),
        ):
            result = dispatch(engine, "right")

        self.assertEqual(result, "")
        self.assertEqual(engine.state.current_room_id, "hallway_janitor")
        self.assertTrue(engine.state.has_flag("step3_rolled"))
        self.assertEqual(
            engine.rooms["hallway_janitor"].exits["left"], "flavor_stairwell"
        )
        self.assertEqual(
            engine.rooms["hallway_janitor"].exits["forward"], "flavor_copy_room"
        )
        self.assertEqual(
            engine.rooms["hallway_janitor"].exits["right"], "flavor_copy_room"
        )
        self.assertEqual(
            engine.rooms["flavor_stairwell"].exits["forward"], "hallway_final"
        )
        self.assertEqual(
            engine.rooms["flavor_stairwell"].exits["back"], "hallway_final"
        )
        self.assertEqual(
            engine.rooms["flavor_copy_room"].exits["forward"], "hallway_janitor"
        )
        self.assertEqual(
            engine.rooms["flavor_copy_room"].exits["back"], "hallway_janitor"
        )

        listen_result = dispatch(engine, "listen")

        self.assertIn("Take the left hall", listen_result)
        self.assertTrue(engine.state.has_flag("step3_song_heard"))

    def test_reentering_puzzle_rooms_reuses_existing_rolls(self) -> None:
        """Verify that re-entering a puzzle room skips the roll when the rolled flag is already set."""
        bathroom_engine = make_engine(start_room="intersection_3way")
        bathroom_engine.state.set_flag("step2_rolled")
        bathroom_engine.state.active_clues["step2_mirror_dir"] = "left"

        with patch("game.commands.player_movement.step2_roll") as step2_roll_mock:
            result = dispatch(bathroom_engine, "forward")

        self.assertEqual(result, "")
        self.assertEqual(bathroom_engine.state.current_room_id, "bathroom")
        self.assertTrue(bathroom_engine.rooms["bathroom"].attributes["sink_running"])
        step2_roll_mock.assert_not_called()

        janitor_engine = make_engine(start_room="intersection_3way_exit")
        janitor_engine.rooms["intersection_3way_exit"].exits["right"] = (
            "hallway_janitor"
        )
        janitor_engine.state.set_flag("step3_rolled")
        janitor_engine.state.active_clues["step3_correct_dir"] = "left"

        with (
            patch("game.commands.player_movement.step3_roll") as step3_roll_mock,
            patch("game.commands.player_movement.random.randint", return_value=1),
            patch(
                "game.commands.player_movement.random.sample",
                return_value=["flavor_stairwell"],
            ),
        ):
            result = dispatch(janitor_engine, "right")

        self.assertEqual(result, "")
        self.assertEqual(janitor_engine.state.current_room_id, "hallway_janitor")
        self.assertEqual(
            janitor_engine.rooms["hallway_janitor"].exits["left"], "flavor_stairwell"
        )
        step3_roll_mock.assert_not_called()

    def test_listen_marks_song_as_heard_and_formats_multiline_chorus(self) -> None:
        """Verify that listen in the janitor hallway returns the formatted chorus and sets the heard flag."""
        engine = make_engine(start_room="hallway_janitor")
        engine.state.active_clues["step3_song_chorus"] = (
            "Take the left hall\nTake it again"
        )

        result = dispatch(engine, "listen")

        self.assertIn("The janitor is humming.", result)
        self.assertIn("\n  Take the left hall\n  Take it again", result)
        self.assertTrue(engine.rooms["hallway_janitor"].attributes["song_heard"])
        self.assertTrue(engine.state.has_flag("step3_song_heard"))

    def test_wrong_and_correct_janitor_turns_behave_differently(self) -> None:
        """Verify that wrong janitor turns loop through flavor rooms while correct turns advance the game."""
        wrong_engine = make_engine(start_room="hallway_janitor")
        wrong_engine.state.active_clues["step3_correct_dir"] = "left"
        wrong_engine.rooms["hallway_janitor"].exits.update(
            {
                "left": "flavor_stairwell",
                "forward": "flavor_copy_room",
                "right": "flavor_copy_room",
            }
        )
        wrong_engine.rooms["flavor_stairwell"].exits["forward"] = "hallway_final"
        wrong_engine.rooms["flavor_stairwell"].exits["back"] = "hallway_final"

        wrong_result = dispatch(wrong_engine, "right")

        self.assertIn("looped back", wrong_result)
        self.assertEqual(wrong_engine.state.current_room_id, "flavor_copy_room")
        self.assertEqual(wrong_engine.state.wrong_turns, 1)

        correct_engine = make_engine(start_room="hallway_janitor")
        correct_engine.state.active_clues["step3_correct_dir"] = "left"
        correct_engine.rooms["hallway_janitor"].exits.update(
            {
                "left": "flavor_stairwell",
                "forward": "flavor_copy_room",
                "right": "flavor_copy_room",
            }
        )
        correct_engine.rooms["flavor_stairwell"].exits["forward"] = "hallway_final"
        correct_engine.rooms["flavor_stairwell"].exits["back"] = "hallway_final"

        correct_result = dispatch(correct_engine, "left")

        self.assertEqual(correct_result, "")
        self.assertEqual(correct_engine.state.current_room_id, "flavor_stairwell")
        self.assertEqual(correct_engine.state.puzzle_step, 3)
        self.assertTrue(correct_engine.state.has_flag("step3_solved"))

    def test_reaching_room_314_sets_win_and_game_over(self) -> None:
        """Verify that entering room_314 ends the session and preserves the ending timer."""
        engine = make_engine(start_room="hallway_final")

        result = dispatch(engine, "forward")

        self.assertEqual(result, "")
        self.assertEqual(engine.state.current_room_id, "room_314")
        self.assertTrue(engine.state.won)
        self.assertTrue(engine.state.game_over)
        self.assertEqual(engine.state.time_remaining, 600)

    def test_reaching_room_314_skips_plain_room_redraw_before_ending(self) -> None:
        """Verify that the plain engine goes straight to the ending after the winning move."""
        engine = make_engine(start_room="hallway_final")

        with patch.object(engine, "signal_transition") as signal_transition_mock:
            result = dispatch(engine, "forward")

        self.assertEqual(result, "")
        self.assertEqual(engine.state.current_room_id, "room_314")
        self.assertTrue(engine.state.won)
        self.assertTrue(engine.state.game_over)
        signal_transition_mock.assert_not_called()
        describe_mock(engine).assert_not_called()


if __name__ == "__main__":
    unittest.main()
