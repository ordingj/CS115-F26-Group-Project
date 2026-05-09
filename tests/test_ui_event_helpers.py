"""Unit tests for engine formatting and event helper behavior.

Verifies :meth:`~game.engine.GameEngine._current_room_view`,
curses rendering helpers, and :class:`~game.event.EventQueue` logic.
"""

from __future__ import annotations

import curses
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, call, patch

from game.curses_engine import UI
from game.engine import CurrentRoomView, GameEngine
from game.event import Event, EventQueue, _build_condition, load_events
from game.curses_rendering import (
    COLOR_EVENT,
    append_wrapped_lines,
    build_room_lines,
    build_system_line_set,
    classify_log_line,
    color_attr,
    init_colors,
    log_attr,
    render_boxed_panel,
)
from game.room import Room
from game.state import GameState
from tests.helpers import make_curses_engine, make_engine


class FakeWindow:
    """Small curses-window stand-in used by the UI helper tests."""

    def __init__(
        self,
        *,
        height: int = 24,
        width: int = 80,
        input_bytes: bytes = b"",
        error_methods: set[str] | None = None,
    ) -> None:
        self.height = height
        self.width = width
        self.input_bytes = input_bytes
        self.error_methods = error_methods or set()
        self.calls: list[tuple[object, ...]] = []

    def _record(self, name: str, *args: object) -> None:
        self.calls.append((name, *args))
        if name in self.error_methods:
            raise curses.error()

    def getmaxyx(self) -> tuple[int, int]:
        self._record("getmaxyx")
        return self.height, self.width

    def erase(self) -> None:
        self._record("erase")

    def refresh(self) -> None:
        self._record("refresh")

    def addstr(self, *args: object) -> None:
        self._record("addstr", *args)

    def border(self) -> None:
        self._record("border")

    def getstr(self, *args: object) -> bytes:
        self._record("getstr", *args)
        return self.input_bytes

    def getch(self) -> int:
        self._record("getch")
        return 0


class GameEngineFormattingTest(unittest.TestCase):
    """Verify shared room-presentation helpers used by both UI layers."""

    def _configured_intersection_engine(self) -> tuple[GameEngine, Room]:
        """Return an intersection-room engine and room with shared clue-test setup."""
        engine = make_engine(
            start_room="intersection_4way",
            time_remaining=125,
            mock_describe=False,
        )
        room = engine.rooms["intersection_4way"]
        room.items = {"poster": "exam poster"}
        room.exits = {
            "left": "intersection_3way",
            "forward": None,
            "right": "flavor_copy_room",
            "back": None,
        }
        engine.state.active_clues.update(
            {
                "step1_correct_dir": "left",
                "step1_clue_type": "light",
            }
        )
        return engine, room

    def test_current_room_view_collects_dynamic_clues_and_metadata(self) -> None:
        """Verify that _current_room_view assembles clue text, exits, items, and formatted time."""
        engine, room = self._configured_intersection_engine()

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
        self.assertIn(UI["intro"]["opening"], output.getvalue())
        self.assertIn(UI["intro"]["teacher"], output.getvalue())

    def test_describe_current_room_renders_shared_room_view_content(self) -> None:
        """Verify that describe_current_room() prints room name, clue, exits, items, and time."""
        engine, _room = self._configured_intersection_engine()

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
        engine._print_intro = Mock()
        engine.describe_current_room = Mock()
        engine._handle_end = Mock()
        engine.state.tick = Mock()
        engine.event_queue.tick = Mock(return_value=["The lights flicker."])
        output = io.StringIO()

        with patch("builtins.input", return_value="quit"), redirect_stdout(output):
            engine.run()

        engine._print_intro.assert_called_once_with()
        engine.describe_current_room.assert_called_once_with()
        engine.state.tick.assert_called_once_with()
        engine._handle_end.assert_called_once_with()
        self.assertTrue(engine.state.quit)
        self.assertIn("The lights flicker.", output.getvalue())
        self.assertIn("Game over.", output.getvalue())


class EventQueueTest(unittest.TestCase):
    """Verify declarative event conditions and queue behaviour."""

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


class CursesEngineFormattingTest(unittest.TestCase):
    """Verify curses-only styling helpers without requiring a live terminal."""

    def test_init_colors_registers_every_defined_color_pair(self) -> None:
        """Verify that init_colors wires all symbolic COLOR_* pairs into curses."""
        with (
            patch("game.curses_rendering.curses.start_color") as start_color,
            patch("game.curses_rendering.curses.use_default_colors") as default_colors,
            patch("game.curses_rendering.curses.init_pair") as init_pair,
        ):
            init_colors()

        start_color.assert_called_once_with()
        default_colors.assert_called_once_with()
        self.assertEqual(init_pair.call_count, 10)

    def test_color_attr_uses_fallback_when_color_pairs_fail(self) -> None:
        """Verify that color_attr still applies modifiers when color lookup fails."""
        with patch(
            "game.curses_rendering.curses.color_pair",
            side_effect=curses.error,
        ):
            attr = color_attr(True, COLOR_EVENT, fallback=8, bold=True, dim=True)

        self.assertEqual(attr, 8 | curses.A_BOLD | curses.A_DIM)

    def test_log_styles_and_attributes_distinguish_message_types(self) -> None:
        """Verify that classify_log_line and log_attr return distinct values for each line category."""
        system_lines = build_system_line_set()

        self.assertEqual(classify_log_line("> help", system_lines), "command")
        self.assertEqual(
            classify_log_line("The lights flicker.", system_lines), "response"
        )
        self.assertEqual(
            classify_log_line("The sign reads: DETOUR", system_lines), "response"
        )
        self.assertEqual(
            classify_log_line("FINAL EXAM: ROOM 314", system_lines), "system"
        )

        with (
            patch(
                "game.curses_rendering.curses.color_pair",
                side_effect=lambda pair_id: pair_id * 256,
            ),
        ):
            event_attr = log_attr("event", True)
            command_attr = log_attr("command", True)
            response_attr = log_attr("response", True)

        self.assertNotEqual(event_attr, command_attr)
        self.assertNotEqual(event_attr, response_attr)
        self.assertNotEqual(command_attr, response_attr)

    def test_build_room_lines_adds_sections_for_details_clues_and_exits(self) -> None:
        """Verify that build_room_lines includes section headers for DETAILS, CLUE, EXITS, and YOU NOTICE."""
        engine = make_curses_engine(start_room="bathroom")
        bathroom = engine.rooms["bathroom"]
        bathroom.attributes["wash_phase"] = 3
        bathroom.attributes["sink_running"] = True

        room_view = engine._current_room_view()

        self.assertIsNotNone(room_view)
        assert room_view is not None

        lines = build_room_lines(room_view, 32)
        sections = [text for style, text in lines if style == "section"]

        self.assertIn(("title", bathroom.name), lines)
        self.assertEqual(sections[:2], ["DETAILS", "CLUE"])
        self.assertIn("EXITS", sections)
        self.assertIn("YOU NOTICE", sections)
        self.assertTrue(
            any(
                style == "clue" and "hands are clean" in text.lower()
                for style, text in lines
            )
        )

    def test_append_wrapped_lines_and_render_boxed_panel_handle_blank_and_error_cases(
        self,
    ) -> None:
        """Verify that wrapping blank chunks and border/addstr failures stay non-fatal."""
        lines: list[tuple[str, str]] = []
        append_wrapped_lines(lines, "body", "first\n\nsecond", 12)
        error_window = FakeWindow(error_methods={"border", "addstr"})

        render_boxed_panel(
            None,
            "ROOM",
            [("body", "ignored")],
            inner_w=10,
            height=3,
            supports_color=False,
            attr_for_style=lambda _style: 0,
        )
        render_boxed_panel(
            error_window,
            "ROOM",
            [("body", "ignored")],
            inner_w=10,
            height=3,
            supports_color=False,
            attr_for_style=lambda _style: 0,
        )

        self.assertIn(("blank", ""), lines)
        self.assertIn(("refresh",), error_window.calls)


class CursesEngineMethodTest(unittest.TestCase):
    """Verify CursesEngine helper methods without launching a real curses session."""

    def test_curses_run_logs_intro_processes_input_and_handles_end(self) -> None:
        """Verify that the curses run loop performs setup, logs intro text, and exits on quit."""
        engine = make_curses_engine()
        stdscr = FakeWindow()
        engine._setup_windows = Mock()
        engine._intro_banner_lines = Mock(return_value=["banner"])
        engine.describe_current_room = Mock()
        engine._get_input = Mock(return_value="quit")
        engine._handle_end = Mock()
        engine._log = Mock()
        engine.event_queue.tick = Mock(return_value=["event"])

        with (
            patch("game.curses_engine.curses.curs_set") as curs_set,
            patch("game.curses_engine.init_colors") as init_colors_mock,
            patch.object(engine, "_supports_color", return_value=True),
        ):
            engine._curses_run(stdscr)

        curs_set.assert_called_once_with(1)
        init_colors_mock.assert_called_once_with()
        engine._setup_windows.assert_called_once_with()
        engine.describe_current_room.assert_called_once_with()
        engine._handle_end.assert_called_once_with()
        self.assertEqual(engine._stdscr, stdscr)
        self.assertIn(call("banner"), engine._log.call_args_list)
        self.assertIn(call("> quit"), engine._log.call_args_list)

    def test_setup_windows_uses_terminal_dimensions_to_create_subwindows(self) -> None:
        """Verify that _setup_windows sizes and stores each curses subwindow."""
        engine = make_curses_engine()
        created_windows = [FakeWindow() for _ in range(4)]
        engine._stdscr = FakeWindow(height=24, width=80)
        engine._refresh_header = Mock()

        with patch(
            "game.curses_engine.curses.newwin",
            side_effect=created_windows,
        ) as newwin:
            engine._setup_windows()

        self.assertEqual(engine._room_h, 11)
        self.assertEqual(engine._log_h, 11)
        self.assertEqual(engine._header_win, created_windows[0])
        self.assertEqual(engine._input_win, created_windows[3])
        self.assertEqual(
            [call.args for call in newwin.call_args_list],
            [(1, 80, 0, 0), (11, 80, 1, 0), (11, 80, 12, 0), (1, 80, 23, 0)],
        )
        engine._refresh_header.assert_called_once_with()

    def test_refresh_header_uses_plain_fallback_when_color_is_off(self) -> None:
        """Verify that the header bar still renders when color support is disabled."""
        engine = make_curses_engine()
        engine._header_win = FakeWindow()
        engine._w = 40

        with patch.object(engine, "_supports_color", return_value=False):
            engine._refresh_header()

        self.assertTrue(any(call[0] == "addstr" for call in engine._header_win.calls))
        self.assertIn(("refresh",), engine._header_win.calls)

    def test_log_wraps_messages_and_uses_style_specific_indentation(self) -> None:
        """Verify that _log wraps text and distinguishes event vs inferred command styles."""
        engine = make_curses_engine()
        engine._w = 16
        engine._refresh_log = Mock()
        engine._system_lines = {"system line"}

        with patch("game.curses_engine.textwrap.wrap", return_value=["wrapped"]):
            engine._log("event text", style="event")
            engine._log("> read sign")

        self.assertEqual(engine._log_lines[0], ("event", "wrapped"))
        self.assertEqual(engine._log_lines[1], ("command", "wrapped"))
        self.assertEqual(engine._refresh_log.call_count, 2)

    def test_refresh_log_passes_recent_lines_to_panel_renderer(self) -> None:
        """Verify that _refresh_log slices to the visible lines before rendering."""
        engine = make_curses_engine()
        engine._w = 20
        engine._log_h = 4
        engine._log_win = FakeWindow()
        engine._log_lines = [
            ("response", "one"),
            ("response", "two"),
            ("response", "three"),
        ]

        with (
            patch.object(engine, "_supports_color", return_value=True),
            patch("game.curses_engine.render_boxed_panel") as render_boxed_panel_mock,
        ):
            engine._refresh_log()

        self.assertEqual(
            render_boxed_panel_mock.call_args.args[2],
            [("response", "two"), ("response", "three")],
        )

    def test_supports_color_handles_curses_errors_and_signal_transition_sets_flag(
        self,
    ) -> None:
        """Verify that supports_color returns False on curses errors and signal_transition toggles the flag."""
        engine = make_curses_engine()

        with patch(
            "game.curses_engine.curses.has_colors",
            side_effect=curses.error,
        ):
            self.assertFalse(engine._supports_color())

        engine.signal_transition()

        self.assertTrue(engine._pending_transition)

    def test_fade_transition_and_describe_current_room_render_the_room_panel(
        self,
    ) -> None:
        """Verify that transitions fade first and describe_current_room then redraws the panel."""
        engine = make_curses_engine()
        engine._room_win = FakeWindow()
        engine._log_win = FakeWindow()
        engine._w = 32
        engine._room_h = 10
        room_view = CurrentRoomView(
            name="Test Room",
            description="A room for testing.",
            clue="A clue.",
            exits=("left",),
            items=("note",),
            time_remaining="9:30",
        )
        engine.signal_transition()

        with (
            patch.object(engine, "_fade_transition") as fade_transition_mock,
            patch.object(engine, "_current_room_view", return_value=room_view),
            patch.object(engine, "_supports_color", return_value=False),
            patch.object(engine, "_refresh_header") as refresh_header_mock,
            patch(
                "game.curses_engine.build_room_lines",
                return_value=[("body", "A room")],
            ),
            patch("game.curses_engine.render_boxed_panel") as render_boxed_panel_mock,
        ):
            engine.describe_current_room()

        fade_transition_mock.assert_called_once_with()
        self.assertEqual(
            render_boxed_panel_mock.call_args.args[:3],
            (engine._room_win, UI["ui_labels"]["panel_room"], [("body", "A room")]),
        )
        refresh_header_mock.assert_called_once_with()
        self.assertFalse(engine._pending_transition)

    def test_fade_transition_tolerates_window_errors(self) -> None:
        """Verify that fade_transition keeps going when one panel raises curses.error."""
        engine = make_curses_engine()
        engine._room_win = FakeWindow()
        engine._log_win = FakeWindow(error_methods={"erase"})

        with patch("game.curses_engine.curses.napms") as napms:
            engine._fade_transition()

        napms.assert_called_once_with(120)

    def test_get_input_reads_prompt_and_restores_terminal_modes(self) -> None:
        """Verify that _get_input returns stripped text and restores curses modes."""
        engine = make_curses_engine()
        engine._input_win = FakeWindow(input_bytes=b"  look mirror  ")
        engine._w = 20

        with (
            patch.object(engine, "_supports_color", return_value=True),
            patch("game.curses_engine.color_attr", return_value=7),
            patch("game.curses_engine.curses.echo") as echo,
            patch("game.curses_engine.curses.nocbreak") as nocbreak,
            patch("game.curses_engine.curses.noecho") as noecho,
            patch("game.curses_engine.curses.cbreak") as cbreak,
        ):
            result = engine._get_input()

        self.assertEqual(result, "look mirror")
        echo.assert_called_once_with()
        nocbreak.assert_called_once_with()
        noecho.assert_called_once_with()
        cbreak.assert_called_once_with()
        self.assertTrue(any(call[0] == "addstr" for call in engine._input_win.calls))

    def test_get_input_returns_blank_when_window_read_fails(self) -> None:
        """Verify that _get_input falls back to an empty string on window read errors."""
        engine = make_curses_engine()
        engine._input_win = FakeWindow(error_methods={"getstr"})

        with (
            patch.object(engine, "_supports_color", return_value=False),
            patch("game.curses_engine.curses.echo"),
            patch("game.curses_engine.curses.nocbreak"),
            patch("game.curses_engine.curses.noecho"),
            patch("game.curses_engine.curses.cbreak"),
        ):
            self.assertEqual(engine._get_input(), "")

    def test_handle_end_logs_border_and_waits_for_keypress(self) -> None:
        """Verify that _handle_end logs the end screen and waits on stdscr."""
        engine = make_curses_engine()
        engine._w = 20
        engine._log = Mock()
        engine._end_lines = Mock(return_value=["Done"])
        engine._input_win = FakeWindow()
        engine._stdscr = FakeWindow()

        with patch("game.curses_engine.curses.noecho") as noecho:
            engine._handle_end()

        self.assertEqual(engine._log.call_args_list[0], call(""))
        self.assertIn(call("Done"), engine._log.call_args_list)
        self.assertIn(call(UI["end"]["press_any_key"]), engine._log.call_args_list)
        noecho.assert_called_once_with()
        self.assertIn(("getch",), engine._stdscr.calls)


if __name__ == "__main__":
    unittest.main()
