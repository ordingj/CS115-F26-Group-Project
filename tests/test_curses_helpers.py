"""Unit tests for curses rendering and curses-engine helper behavior."""

from __future__ import annotations

import curses
import unicodedata
from typing import Any, cast
import unittest
from unittest.mock import call, patch

from game.engine.curses_engine import UI
from game.engine.curses_rendering import (
    COLOR_EVENT,
    COLOR_HEADER,
    COLOR_HEADER_DANGER,
    COLOR_HEADER_WARNING,
    PANEL_PAD,
    append_wrapped_lines,
    build_room_lines,
    build_system_line_set,
    classify_log_line,
    color_attr,
    init_colors,
    log_attr,
    render_boxed_panel,
)
from game.engine.engine import CurrentRoomView
from tests.helpers import dispatch, make_curses_engine


def _display_cell_width(text: str) -> int:
    """Return a conservative terminal-cell width for one rendered string."""
    width = 0
    for char in text:
        if not char or unicodedata.combining(char):
            continue
        if unicodedata.category(char).startswith("C"):
            continue
        width += 2 if unicodedata.east_asian_width(char) in {"A", "F", "W"} else 1
    return width


class FakeWindow:
    """Small curses-window stand-in used by the curses helper tests."""

    def __init__(
        self,
        *,
        height: int = 24,
        width: int = 80,
        input_bytes: bytes = b"",
        input_keys: list[object] | None = None,
        error_methods: set[str] | None = None,
    ) -> None:
        """Store the scripted window size, input stream, and failure hooks."""
        self.height = height
        self.width = width
        self.input_bytes = input_bytes
        self.input_keys = list(input_keys or [])
        self.error_methods = error_methods or set()
        self.calls: list[tuple[object, ...]] = []
        self.timeout_ms: int | None = None

    def _record(self, name: str, *args: object) -> None:
        """Record a curses call and raise when that method is configured to fail."""
        self.calls.append((name, *args))
        if name in self.error_methods:
            raise curses.error()

    def getmaxyx(self) -> tuple[int, int]:
        """Return the scripted fake window dimensions."""
        self._record("getmaxyx")
        return self.height, self.width

    def erase(self) -> None:
        """Record an erase call."""
        self._record("erase")

    def refresh(self) -> None:
        """Record a refresh call."""
        self._record("refresh")

    def addstr(self, *args: object) -> None:
        """Record text written to the fake window."""
        self._record("addstr", *args)

    def border(self) -> None:
        """Record a border draw request."""
        self._record("border")

    def keypad(self, enabled: bool) -> None:
        """Record keypad-mode changes."""
        self._record("keypad", enabled)

    def timeout(self, delay: int) -> None:
        """Record the blocking timeout used for keyboard reads."""
        self._record("timeout", delay)
        self.timeout_ms = delay

    def leaveok(self, enabled: bool) -> None:
        """Record whether refreshes should leave the cursor position unspecified."""
        self._record("leaveok", enabled)

    def getstr(self, *args: object) -> bytes:
        """Return the scripted byte input for blocking string reads."""
        self._record("getstr", *args)
        return self.input_bytes

    def get_wch(self) -> object:
        """Return the next scripted wide-character input event."""
        self._record("get_wch")
        if not self.input_keys:
            if self.timeout_ms is not None and self.timeout_ms >= 0:
                raise curses.error("no input")
            raise curses.error()
        return self.input_keys.pop(0)

    def getch(self) -> int:
        """Return a neutral key code for end-screen waits."""
        self._record("getch")
        return 0


class StrictWidthWindow(FakeWindow):
    """Fake window that raises when ``addstr`` would overflow its visible area."""

    def addstr(self, *args: object) -> None:
        """Record text writes and reject strings that exceed the usable width."""
        self._record("addstr", *args)
        if len(args) < 3:
            return
        row, col, text = args[:3]
        if (
            not isinstance(row, int)
            or not isinstance(col, int)
            or not isinstance(text, str)
        ):
            return
        usable_width = max(0, self.width - col - 1)
        if _display_cell_width(text) > usable_width:
            raise curses.error()


class CursesEngineFormattingTest(unittest.TestCase):
    """Verify curses-only styling helpers without requiring a live terminal."""

    def test_init_colors_registers_every_defined_color_pair(self) -> None:
        """Verify that init_colors wires all symbolic COLOR_* pairs into curses."""
        with (
            patch("game.engine.curses_rendering.curses.start_color") as start_color,
            patch(
                "game.engine.curses_rendering.curses.use_default_colors"
            ) as default_colors,
            patch("game.engine.curses_rendering.curses.init_pair") as init_pair,
        ):
            init_colors()

        start_color.assert_called_once_with()
        default_colors.assert_called_once_with()
        self.assertEqual(init_pair.call_count, 12)

    def test_color_attr_uses_fallback_when_color_pairs_fail(self) -> None:
        """Verify that color_attr still applies modifiers when color lookup fails."""
        with patch(
            "game.engine.curses_rendering.curses.color_pair",
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
                "game.engine.curses_rendering.curses.color_pair",
                side_effect=lambda pair_id: pair_id * 256,
            ),
        ):
            event_attr = log_attr("event", True)
            command_attr = log_attr("command", True)
            response_attr = log_attr("response", True)

        self.assertNotEqual(event_attr, command_attr)
        self.assertNotEqual(event_attr, response_attr)
        self.assertNotEqual(command_attr, response_attr)

    def test_build_room_lines_shows_clue_text_without_clue_header(self) -> None:
        """Verify that build_room_lines keeps clue text but no longer prints a CLUE section label."""
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
        self.assertEqual(sections[0], "DETAILS")
        self.assertIn("EXITS", sections)
        self.assertIn("YOU NOTICE", sections)
        self.assertNotIn("CLUE", sections)
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

    def test_render_boxed_panel_clips_wide_glyph_lines_to_safe_cell_width(self) -> None:
        """Verify that render_boxed_panel trims wide glyphs before writing narrow lines."""
        narrow_window = StrictWidthWindow(width=28)

        render_boxed_panel(
            cast(Any, narrow_window),
            "ROOM",
            [("body", "YOU MADE IT TO ROOM 314 —")],
            inner_w=25,
            height=4,
            supports_color=False,
            attr_for_style=lambda _style: 0,
        )

        body_lines = [
            cast(str, call_args[3])
            for call_args in narrow_window.calls
            if call_args[:3] == ("addstr", 1, PANEL_PAD)
            and isinstance(call_args[3], str)
        ]

        self.assertEqual(body_lines, ["YOU MADE IT TO ROOM 314"])
        self.assertTrue(
            all(_display_cell_width(line) <= 25 for line in body_lines),
        )


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
            patch("game.engine.curses_engine.curses.curs_set") as curs_set,
            patch("game.engine.curses_engine.init_colors") as init_colors_mock,
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
                "game.engine.curses_engine.curses.newwin",
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
        self.assertIn(("leaveok", True), created_windows[0].calls)
        self.assertIn(("leaveok", True), created_windows[1].calls)
        self.assertIn(("leaveok", True), created_windows[2].calls)
        self.assertIn(("leaveok", False), created_windows[3].calls)
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

    def test_refresh_header_colors_time_by_remaining_threshold(self) -> None:
        """Verify that the timer switches header colors at warning thresholds."""
        engine = make_curses_engine()
        header_win = FakeWindow()
        engine_any = cast(Any, engine)
        engine_any._header_win = header_win
        engine._w = 40
        cases = [
            (600, COLOR_HEADER),
            (299, COLOR_HEADER_WARNING),
            (59, COLOR_HEADER_DANGER),
        ]

        with (
            patch.object(engine, "_supports_color", return_value=True),
            patch(
                "game.engine.curses_engine.color_attr",
                side_effect=lambda _supports_color, pair_id, **_kwargs: pair_id,
            ),
        ):
            for time_remaining, expected_attr in cases:
                with self.subTest(time_remaining=time_remaining):
                    header_win.calls.clear()
                    engine.state.time_remaining = time_remaining

                    engine._refresh_header()

                    timer_calls = [
                        call_args
                        for call_args in header_win.calls
                        if call_args[0] == "addstr"
                        and isinstance(call_args[3], str)
                        and call_args[3].startswith(
                            UI["ui_labels"]["header_time_prefix"]
                        )
                    ]

                    self.assertEqual(timer_calls[-1][-1], expected_attr)

    def test_log_wraps_messages_and_uses_style_specific_indentation(self) -> None:
        """Verify that _log wraps text and distinguishes event vs inferred command styles."""
        engine = make_curses_engine()
        engine._w = 16
        engine._system_lines = {"system line"}

        with (
            patch.object(engine, "_refresh_log") as refresh_log_mock,
            patch("game.engine.curses_engine.textwrap.wrap", return_value=["wrapped"]),
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
            patch(
                "game.engine.curses_engine.render_boxed_panel"
            ) as render_boxed_panel_mock,
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
            "game.engine.curses_engine.curses.has_colors",
            side_effect=curses.error,
        ):
            self.assertFalse(engine._supports_color())

        engine.signal_transition()

        self.assertTrue(engine._pending_transition)

    def test_fade_transition_and_describe_current_room_redraw_both_panels(
        self,
    ) -> None:
        """Verify that transitions fade first and describe_current_room redraws room and log panels."""
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
            patch.object(engine, "_refresh_log") as refresh_log_mock,
            patch.object(engine, "_refresh_header") as refresh_header_mock,
            patch(
                "game.engine.curses_engine.build_room_lines",
                return_value=[("body", "A room")],
            ),
            patch(
                "game.engine.curses_engine.render_boxed_panel"
            ) as render_boxed_panel_mock,
        ):
            engine.describe_current_room()

        fade_transition_mock.assert_called_once_with()
        self.assertEqual(
            render_boxed_panel_mock.call_args.args[:3],
            (room_win, UI["ui_labels"]["panel_room"], [("body", "A room")]),
        )
        self.assertEqual(render_boxed_panel_mock.call_args.kwargs["inner_w"], 28)
        refresh_log_mock.assert_called_once_with()
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

        with patch("game.engine.curses_engine.curses.napms") as napms:
            engine._fade_transition()

        napms.assert_called_once_with(120)

    def test_reaching_room_314_outside_live_curses_still_sets_win_state(self) -> None:
        """Verify that the final-room move path stays safe and ends immediately in a win."""
        engine = make_curses_engine(start_room="hallway_final")

        result = dispatch(engine, "forward")

        self.assertEqual(result, "")
        self.assertEqual(engine.state.current_room_id, "room_314")
        self.assertTrue(engine.state.won)
        self.assertTrue(engine.state.game_over)

    def test_reaching_room_314_in_curses_still_requests_a_redraw(self) -> None:
        """Verify that the winning move still redraws the destination before the end screen."""
        engine = make_curses_engine(start_room="hallway_final")

        with (
            patch.object(engine, "signal_transition") as signal_transition_mock,
            patch.object(engine, "describe_current_room") as describe_current_room_mock,
        ):
            result = dispatch(engine, "forward")

        self.assertEqual(result, "")
        self.assertEqual(engine.state.current_room_id, "room_314")
        self.assertTrue(engine.state.won)
        self.assertTrue(engine.state.game_over)
        signal_transition_mock.assert_called_once_with()
        describe_current_room_mock.assert_called_once_with()

    def test_get_input_reads_prompt_and_restores_terminal_modes(self) -> None:
        """Verify that _get_input ignores arrow keys and returns stripped text."""
        engine = make_curses_engine()
        input_win = FakeWindow(
            input_keys=[curses.KEY_DOWN, *list("  look mirror  "), "\n"],
        )
        engine_any = cast(Any, engine)
        engine_any._input_win = input_win
        engine._w = 20

        with (
            patch.object(engine, "_supports_color", return_value=True),
            patch("game.engine.curses_engine.color_attr", return_value=7),
        ):
            result = engine._get_input()

        self.assertEqual(result, "look mirror")
        self.assertIn(("keypad", True), input_win.calls)
        self.assertIn(("timeout", 1000), input_win.calls)
        self.assertIn(("timeout", -1), input_win.calls)
        self.assertTrue(any(call[0] == "get_wch" for call in input_win.calls))
        self.assertTrue(any(call[0] == "addstr" for call in input_win.calls))

    def test_get_input_ignores_stdscr_when_input_window_is_available(self) -> None:
        """Verify that _get_input reads from the prompt window, not stdscr."""
        engine = make_curses_engine()
        input_win = FakeWindow(input_keys=[*list("help"), "\n"])
        stdscr = FakeWindow(input_keys=[*list("quit"), "\n"])
        engine_any = cast(Any, engine)
        engine_any._input_win = input_win
        engine_any._stdscr = stdscr
        engine._w = 20

        with (
            patch.object(engine, "_supports_color", return_value=False),
        ):
            result = engine._get_input()

        self.assertEqual(result, "help")
        self.assertIn(("keypad", True), input_win.calls)
        self.assertIn(("timeout", 1000), input_win.calls)
        self.assertIn(("timeout", -1), input_win.calls)
        self.assertFalse(any(call[0] == "get_wch" for call in stdscr.calls))

    def test_get_input_polls_live_timer_until_timeout_ends_the_game(self) -> None:
        """Verify that idle input loops refresh the header and exit on timeout."""
        engine = make_curses_engine()
        input_win = FakeWindow()
        header_win = FakeWindow()
        engine_any = cast(Any, engine)
        engine_any._input_win = input_win
        engine_any._header_win = header_win
        engine._w = 20

        sync_results = [False, True]

        def _sync_time() -> bool:
            """Drive two polling iterations so the second one ends the session."""
            changed = sync_results.pop(0)
            if changed:
                engine.state.time_remaining = 0
                engine.state.game_over = True
            else:
                engine.state.time_remaining = 9
            return changed

        with (
            patch.object(engine, "_supports_color", return_value=False),
            patch.object(
                engine.state, "sync_time", side_effect=_sync_time
            ) as sync_mock,
        ):
            result = engine._get_input()

        self.assertEqual(result, "")
        self.assertEqual(sync_mock.call_count, 2)
        self.assertIn(("timeout", 1000), input_win.calls)
        self.assertIn(("timeout", -1), input_win.calls)
        self.assertGreaterEqual(header_win.calls.count(("refresh",)), 2)

    def test_get_input_returns_blank_when_window_read_fails(self) -> None:
        """Verify that _get_input falls back to an empty string on window read errors."""
        engine = make_curses_engine()
        input_win = FakeWindow(error_methods={"get_wch"})
        engine_any = cast(Any, engine)
        engine_any._input_win = input_win

        with (
            patch.object(engine, "_supports_color", return_value=False),
        ):
            self.assertEqual(engine._get_input(), "")

    def test_handle_end_renders_dedicated_panels_and_waits_for_keypress(self) -> None:
        """Verify that _handle_end renders end panels and waits on the input bar."""
        engine = make_curses_engine()
        room_win = FakeWindow()
        log_win = FakeWindow()
        input_win = FakeWindow()
        stdscr = FakeWindow()
        engine_any = cast(Any, engine)
        engine_any._room_win = room_win
        engine_any._log_win = log_win
        engine_any._input_win = input_win
        engine_any._stdscr = stdscr
        engine._w = 80

        with (
            patch.object(engine, "_render_panel") as render_panel_mock,
            patch.object(engine, "_end_lines", return_value=["Done"]),
            patch("game.engine.curses_engine.curses.noecho") as noecho,
            patch("game.engine.curses_engine.curses.flushinp") as flushinp,
        ):
            engine._handle_end()

        self.assertEqual(render_panel_mock.call_count, 2)
        room_call, log_call = render_panel_mock.call_args_list
        self.assertEqual(room_call.args[:2], (room_win, UI["ui_labels"]["panel_room"]))
        self.assertTrue(any(line == "Done" for _, line in room_call.args[2]))
        self.assertEqual(log_call.args[:2], (log_win, UI["ui_labels"]["panel_log"]))
        self.assertTrue(
            any("Press Enter to replay" in line for _, line in log_call.args[2])
        )
        noecho.assert_called_once_with()
        flushinp.assert_called_once_with()
        self.assertIn(("getch",), input_win.calls)
        self.assertFalse(any(call[0] == "getch" for call in stdscr.calls))

    def test_handle_end_renders_each_ending_variant_and_waits_for_keypress(
        self,
    ) -> None:
        """Verify that every ending variant waits for replay input on the prompt bar."""
        cases = [
            (True, 300, "TOMORROW."),
            (True, 240, "already in progress"),
            (False, 0, "TIME'S UP."),
        ]

        for won, time_remaining, expected in cases:
            with self.subTest(won=won, time_remaining=time_remaining):
                engine = make_curses_engine()
                room_win = FakeWindow()
                log_win = FakeWindow()
                input_win = FakeWindow()
                stdscr = FakeWindow()
                engine_any = cast(Any, engine)
                engine_any._room_win = room_win
                engine_any._log_win = log_win
                engine_any._input_win = input_win
                engine_any._stdscr = stdscr
                engine._w = 80
                engine.state.won = won
                engine.state.time_remaining = time_remaining

                with (
                    patch.object(engine, "_render_panel") as render_panel_mock,
                    patch("game.engine.curses_engine.curses.noecho") as noecho,
                    patch("game.engine.curses_engine.curses.flushinp") as flushinp,
                ):
                    engine._handle_end()

                self.assertEqual(render_panel_mock.call_count, 2)
                room_call, log_call = render_panel_mock.call_args_list
                self.assertTrue(any(expected in line for _, line in room_call.args[2]))
                self.assertTrue(
                    any(
                        UI["end"]["press_enter_to_replay"] in line
                        for _, line in log_call.args[2]
                    )
                )
                noecho.assert_called_once_with()
                flushinp.assert_called_once_with()
                self.assertIn(("getch",), input_win.calls)
                self.assertFalse(any(call[0] == "getch" for call in stdscr.calls))

    def test_handle_end_falls_back_to_stdscr_when_input_bar_is_missing(self) -> None:
        """Verify that _handle_end still reads a key when no input window exists."""
        engine = make_curses_engine()
        room_win = FakeWindow()
        log_win = FakeWindow()
        stdscr = FakeWindow()
        engine_any = cast(Any, engine)
        engine_any._room_win = room_win
        engine_any._log_win = log_win
        engine_any._input_win = None
        engine_any._stdscr = stdscr
        engine._w = 80

        with (
            patch.object(engine, "_render_panel"),
            patch.object(engine, "_end_lines", return_value=["Done"]),
            patch("game.engine.curses_engine.curses.noecho"),
            patch("game.engine.curses_engine.curses.flushinp"),
        ):
            engine._handle_end()

        self.assertIn(("getch",), stdscr.calls)


if __name__ == "__main__":
    unittest.main()
