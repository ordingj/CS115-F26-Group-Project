"""Unit tests for curses rendering and curses-engine helper behavior."""

from __future__ import annotations

import curses
from typing import Any, cast
import unittest
from unittest.mock import call, patch

from game.curses_engine import UI
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
from game.engine import CurrentRoomView
from tests.helpers import make_curses_engine


class FakeWindow:
    """Small curses-window stand-in used by the curses helper tests."""

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

    def test_build_room_lines_skips_empty_optional_sections(self) -> None:
        """Verify that empty clue, exits, and items do not add extra optional sections."""
        room_view = CurrentRoomView(
            name="Spare Room",
            description="Bare walls.",
            clue="",
            exits=(),
            items=(),
            time_remaining="9:59",
        )

        lines = build_room_lines(room_view, 32)

        self.assertEqual(
            [text for style, text in lines if style == "section"],
            ["DETAILS"],
        )
        self.assertFalse(any(style == "clue" for style, _text in lines))
        self.assertFalse(any(style == "exit" for style, _text in lines))
        self.assertFalse(any(style == "item" for style, _text in lines))

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
            cast(Any, error_window),
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

        with (
            patch.object(engine, "_setup_windows") as setup_windows_mock,
            patch.object(engine, "_intro_banner_lines", return_value=["banner"]),
            patch.object(engine, "describe_current_room") as describe_mock,
            patch.object(engine, "_get_input", return_value="quit"),
            patch.object(engine, "_handle_end") as handle_end_mock,
            patch.object(engine, "_log") as log_mock,
            patch.object(engine.event_queue, "tick", return_value=["event"]),
            patch("game.curses_engine.curses.curs_set") as curs_set,
            patch("game.curses_engine.init_colors") as init_colors_mock,
            patch.object(engine, "_supports_color", return_value=True),
        ):
            engine._curses_run(cast(Any, stdscr))

        curs_set.assert_called_once_with(1)
        init_colors_mock.assert_called_once_with()
        setup_windows_mock.assert_called_once_with()
        describe_mock.assert_called_once_with()
        handle_end_mock.assert_called_once_with()
        self.assertEqual(engine._stdscr, stdscr)
        self.assertIn(call("banner"), log_mock.call_args_list)
        self.assertIn(call("> quit"), log_mock.call_args_list)

    def test_setup_windows_uses_terminal_dimensions_to_create_subwindows(self) -> None:
        """Verify that _setup_windows sizes and stores each curses subwindow."""
        engine = make_curses_engine()
        created_windows = [FakeWindow() for _ in range(4)]
        stdscr = FakeWindow(height=24, width=80)
        engine_any = cast(Any, engine)
        engine_any._stdscr = stdscr

        with (
            patch.object(engine, "_refresh_header") as refresh_header_mock,
            patch(
                "game.curses_engine.curses.newwin",
                side_effect=created_windows,
            ) as newwin,
        ):
            engine._setup_windows()

        self.assertEqual(engine._room_h, 11)
        self.assertEqual(engine._log_h, 11)
        self.assertEqual(engine._header_win, created_windows[0])
        self.assertEqual(engine._input_win, created_windows[3])
        self.assertEqual(
            [call.args for call in newwin.call_args_list],
            [(1, 80, 0, 0), (11, 80, 1, 0), (11, 80, 12, 0), (1, 80, 23, 0)],
        )
        refresh_header_mock.assert_called_once_with()

    def test_refresh_header_uses_plain_fallback_when_color_is_off(self) -> None:
        """Verify that the header bar still renders when color support is disabled."""
        engine = make_curses_engine()
        header_win = FakeWindow()
        engine_any = cast(Any, engine)
        engine_any._header_win = header_win
        engine._w = 40

        with patch.object(engine, "_supports_color", return_value=False):
            engine._refresh_header()

        self.assertTrue(any(call[0] == "addstr" for call in header_win.calls))
        self.assertIn(("refresh",), header_win.calls)

    def test_log_wraps_messages_and_uses_style_specific_indentation(self) -> None:
        """Verify that _log wraps text and distinguishes event vs inferred command styles."""
        engine = make_curses_engine()
        engine._w = 16
        engine._system_lines = {"system line"}

        with (
            patch.object(engine, "_refresh_log") as refresh_log_mock,
            patch("game.curses_engine.textwrap.wrap", return_value=["wrapped"]),
        ):
            engine._log("event text", style="event")
            engine._log("> read sign")

        self.assertEqual(engine._log_lines[0], ("event", "wrapped"))
        self.assertEqual(engine._log_lines[1], ("command", "wrapped"))
        self.assertEqual(refresh_log_mock.call_count, 2)

    def test_refresh_log_passes_recent_lines_to_panel_renderer(self) -> None:
        """Verify that _refresh_log slices to the visible lines before rendering."""
        engine = make_curses_engine()
        log_win = FakeWindow()
        engine_any = cast(Any, engine)
        engine_any._log_win = log_win
        engine._w = 20
        engine._log_h = 4
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
        self.assertEqual(render_boxed_panel_mock.call_args.kwargs["inner_w"], 16)

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
        room_win = FakeWindow()
        log_win = FakeWindow()
        engine_any = cast(Any, engine)
        engine_any._room_win = room_win
        engine_any._log_win = log_win
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
            (room_win, UI["ui_labels"]["panel_room"], [("body", "A room")]),
        )
        self.assertEqual(render_boxed_panel_mock.call_args.kwargs["inner_w"], 28)
        refresh_header_mock.assert_called_once_with()
        self.assertFalse(engine._pending_transition)

    def test_fade_transition_tolerates_window_errors(self) -> None:
        """Verify that fade_transition keeps going when one panel raises curses.error."""
        engine = make_curses_engine()
        room_win = FakeWindow()
        log_win = FakeWindow(error_methods={"erase"})
        engine_any = cast(Any, engine)
        engine_any._room_win = room_win
        engine_any._log_win = log_win

        with patch("game.curses_engine.curses.napms") as napms:
            engine._fade_transition()

        napms.assert_called_once_with(120)

    def test_get_input_reads_prompt_and_restores_terminal_modes(self) -> None:
        """Verify that _get_input returns stripped text and restores curses modes."""
        engine = make_curses_engine()
        input_win = FakeWindow(input_bytes=b"  look mirror  ")
        engine_any = cast(Any, engine)
        engine_any._input_win = input_win
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
        self.assertTrue(any(call[0] == "addstr" for call in input_win.calls))

    def test_get_input_returns_blank_when_window_read_fails(self) -> None:
        """Verify that _get_input falls back to an empty string on window read errors."""
        engine = make_curses_engine()
        input_win = FakeWindow(error_methods={"getstr"})
        engine_any = cast(Any, engine)
        engine_any._input_win = input_win

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
        input_win = FakeWindow()
        stdscr = FakeWindow()
        engine_any = cast(Any, engine)
        engine_any._input_win = input_win
        engine_any._stdscr = stdscr
        engine._w = 20

        with (
            patch.object(engine, "_log") as log_mock,
            patch.object(engine, "_end_lines", return_value=["Done"]),
            patch("game.curses_engine.curses.noecho") as noecho,
        ):
            engine._handle_end()

        self.assertEqual(log_mock.call_args_list[0], call(""))
        self.assertIn(call("Done"), log_mock.call_args_list)
        self.assertIn(call(UI["end"]["press_any_key"]), log_mock.call_args_list)
        noecho.assert_called_once_with()
        self.assertIn(("getch",), stdscr.calls)


if __name__ == "__main__":
    unittest.main()
