"""CursesEngine – curses-based split-pane UI for the text adventure engine.

Layout (top to bottom):
  1-line header  – game title and time remaining
  room panel     – current room name, description, exits, and visible items
  log panel      – event messages and command responses (newest at bottom)
  1-line input   – command prompt ("> _")
"""

from __future__ import annotations

import curses
import textwrap
from collections.abc import Callable

from game.commands.command import CommandRegistry
from game.engine.curses_rendering import (
    COLOR_HEADER,
    COLOR_HEADER_DANGER,
    COLOR_HEADER_WARNING,
    COLOR_PROMPT,
    PANEL_PAD,
    build_room_lines,
    build_system_line_set,
    classify_log_line,
    color_attr,
    init_colors,
    log_attr,
    render_boxed_panel,
    room_attr,
    truncate_for_display,
)
from game.engine.engine import GameEngine, UI
from game.event import EventQueue
from game.room import Room
from game.state import GameState

# Fraction of the terminal height devoted to the room panel.
_ROOM_RATIO = 0.48


class CursesEngine(GameEngine):
    """GameEngine subclass that renders in a curses split-pane layout.

    The terminal is divided (top to bottom) into a 1-line header, a room
    panel, a scrolling log panel, and a 1-line input bar.  All game logic
    lives in the parent :class:`~game.engine.engine.GameEngine`; this class only
    overrides the I/O methods.
    """

    def __init__(
        self,
        rooms: dict[str, Room],
        state: GameState,
        registry: CommandRegistry,
        event_queue: EventQueue,
    ) -> None:
        """Initialise the curses engine, forwarding all arguments to the parent.

        Parameters
        ----------
        rooms : dict[str, Room]
            Mapping of ``room_id`` → :class:`~game.room.Room`.
        state : GameState
            Mutable game state for this session.
        registry : CommandRegistry
            Populated command registry.
        event_queue : EventQueue
            Ambient event queue.
        """
        super().__init__(rooms, state, registry, event_queue)
        self._log_lines: list[tuple[str, str]] = []
        self._system_lines = build_system_line_set()
        self._pending_transition: bool = False
        # Dimensions are set by _setup_windows(); defaults avoid crashes if
        # a helper is called before the curses loop starts.
        self._w: int = 80
        self._room_h: int = 12
        self._log_h: int = 12
        self._stdscr: curses.window | None = None
        self._header_win: curses.window | None = None
        self._room_win: curses.window | None = None
        self._log_win: curses.window | None = None
        self._input_win: curses.window | None = None

    # ── public API override ────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the game inside :func:`curses.wrapper` for automatic cleanup.

        :func:`curses.wrapper` saves/restores terminal state and calls
        :meth:`_curses_run` with the root ``stdscr`` window.
        """
        curses.wrapper(self._curses_run)

    # ── curses run loop ────────────────────────────────────────────────────────

    def _curses_run(self, stdscr: curses.window) -> None:
        """Main game loop executed inside the curses wrapper.

        Called by :meth:`run` via :func:`curses.wrapper`.  Mirrors the
        parent's :meth:`~game.engine.engine.GameEngine.run` loop but routes all
        output through the curses panel helpers instead of ``print``.

        Parameters
        ----------
        stdscr : curses.window
            Full-screen window provided by :func:`curses.wrapper`.
        """
        self._stdscr = stdscr
        curses.curs_set(1)
        if self._supports_color():
            init_colors()
        self.state.start_countdown()

        self._setup_windows()

        self._start_session()
        self._play_until_game_over()
        self._handle_end()

    def _start_session(self) -> None:
        """Log the curses intro banner and render the starting room once."""
        intro = UI["intro"]
        for line in self._intro_banner_lines():
            self._log(line)
        self._log(intro["curses_subtitle"])
        self._log(intro["help_hint"])
        self._log("")
        self.describe_current_room()

    def _emit_event(self, message: str) -> None:
        """Append one ambient event message to the curses log."""
        self._log(message, style="event")

    def _before_command_prompt(self) -> None:
        """Refresh the header before each curses input prompt."""
        self._refresh_header()

    def _read_command(self) -> str:
        """Return one raw player command line from the curses input bar."""
        return self._get_input()

    def _echo_command(self, raw: str) -> None:
        """Echo one raw player command into the curses log."""
        self._log("> " + raw)

    def _emit_command_result(self, result: str) -> None:
        """Append one command result string to the curses log."""
        self._log(result)

    # ── window setup ───────────────────────────────────────────────────────────

    def _setup_windows(self) -> None:
        """Create and size the four curses sub-windows from current terminal dimensions.

        Window layout (rows, from top):

        - **Row 0**: 1-row header (title + time remaining).
        - **Rows 1…room_h**: room panel (name, description, clue, exits, items).
        - **Rows room_h+1…h-2**: log panel (event messages, command results).
        - **Row h-1**: 1-row input bar (prompt + player typing area).
        """
        h, w = self._stdscr.getmaxyx()  # type: ignore[union-attr]
        self._w = w
        room_h = max(6, int(h * _ROOM_RATIO))
        log_h = max(4, h - room_h - 2)  # 1 header + 1 input = 2 reserved rows
        self._room_h = room_h
        self._log_h = log_h

        self._header_win = curses.newwin(1, w, 0, 0)
        self._room_win = curses.newwin(room_h, w, 1, 0)
        self._log_win = curses.newwin(log_h, w, 1 + room_h, 0)
        self._input_win = curses.newwin(1, w, h - 1, 0)

        for win in (self._header_win, self._room_win, self._log_win):
            try:
                win.leaveok(True)
            except curses.error:
                pass
        try:
            self._input_win.leaveok(False)
        except curses.error:
            pass

        self._refresh_header()

    # ── display helpers ────────────────────────────────────────────────────────

    def _refresh_header(self) -> None:
        """Redraw the top title/time bar with the current time remaining."""
        win = self._header_win
        if win is None:
            return
        self.state.sync_time()
        win.erase()
        labels = UI["ui_labels"]
        title = "  " + UI["intro"]["title"]
        time_str = labels["header_time_prefix"] + self.state.formatted_time() + "  "
        gap = max(0, self._w - len(title) - len(time_str))
        line = title + " " * gap + time_str
        try:
            supports_color = self._supports_color()
            header_attr = (
                color_attr(
                    supports_color,
                    COLOR_HEADER,
                    fallback=curses.A_REVERSE,
                    bold=True,
                )
                if supports_color
                else curses.A_REVERSE
            )
            if self.state.time_remaining < 60:
                time_attr = color_attr(
                    supports_color,
                    COLOR_HEADER_DANGER,
                    fallback=curses.A_REVERSE,
                    bold=True,
                )
            elif self.state.time_remaining < 300:
                time_attr = color_attr(
                    supports_color,
                    COLOR_HEADER_WARNING,
                    fallback=curses.A_REVERSE,
                    bold=True,
                )
            else:
                time_attr = header_attr
            win.addstr(0, 0, truncate_for_display(line, self._w), header_attr)
            win.addstr(0, max(0, self._w - len(time_str)), time_str, time_attr)
        except curses.error:
            pass
        win.refresh()

    def _log(self, msg: str, *, style: str | None = None) -> None:
        """Append *msg* to the scrolling log panel, wrapping long lines.

        Parameters
        ----------
        msg : str
            Message to append.  Multi-line strings are split on ``\\n``;
            each segment is word-wrapped independently.
        style : str or None, optional
            Explicit style tag (e.g. ``"event"``).  When ``None``,
            :func:`~game.curses_rendering.classify_log_line` infers the
            style from the line's content.
        """
        inner_w = self._panel_inner_width()
        for part in msg.split("\n"):
            line_style = (
                style
                if style is not None
                else classify_log_line(part, self._system_lines)
            )
            subsequent_indent = ""
            if line_style == "event":
                subsequent_indent = "    "
            elif line_style == "command":
                subsequent_indent = "  "
            wrapped = (
                textwrap.wrap(part, inner_w, subsequent_indent=subsequent_indent)
                if part.strip()
                else [""]
            )
            self._log_lines.extend((line_style, line) for line in wrapped)
        self._refresh_log()

    def _panel_inner_width(self) -> int:
        """Return the usable content width inside boxed room/log panels."""
        return max(1, self._w - (PANEL_PAD * 2))

    def _render_panel(
        self,
        win: curses.window | None,
        title: str,
        lines: list[tuple[str, str]],
        *,
        height: int,
        attr_resolver: Callable[[str, bool], int],
    ) -> None:
        """Render one boxed panel using the shared width and color setup."""
        supports_color = self._supports_color()
        render_boxed_panel(
            win,
            title,
            lines,
            inner_w=self._panel_inner_width(),
            height=height,
            supports_color=supports_color,
            attr_for_style=lambda style: attr_resolver(style, supports_color),
        )

    def _refresh_log(self) -> None:
        """Re-render the scrolling log panel, showing only the most recent lines."""
        inner_h = max(0, self._log_h - 2)
        visible = self._log_lines[-inner_h:]
        self._render_panel(
            self._log_win,
            UI["ui_labels"]["panel_log"],
            visible,
            height=self._log_h,
            attr_resolver=log_attr,
        )

    def _supports_color(self) -> bool:
        """Return ``True`` when curses colour output is currently available.

        Returns
        -------
        bool
            Result of :func:`curses.has_colors`, or ``False`` if curses
            raises an error (e.g. when not in a curses context).
        """
        try:
            return curses.has_colors()
        except curses.error:
            return False

    def signal_transition(self) -> None:
        """Arm the fade-to-black transition for the next room description.

        Sets ``_pending_transition`` so :meth:`describe_current_room` will
        call :meth:`_fade_transition` before re-drawing the room panel.
        """
        self._pending_transition = True

    def should_render_arrival_room(self) -> bool:
        """Keep the destination room visible before the curses end screen."""
        return True

    # ── room display override ──────────────────────────────────────────────────

    def _fade_transition(self) -> None:
        """Briefly blank the room and log panels to simulate a room transition.

        Erases both panels and pauses for ~120 ms before returning so the
        caller can redraw with new content — producing a simple cut-to-black
        effect without requiring animation support.
        """
        for win in (self._room_win, self._log_win):
            if win is not None:
                try:
                    win.erase()
                    win.refresh()
                except curses.error:
                    pass
        try:
            curses.napms(120)
        except curses.error:
            pass

    def describe_current_room(self) -> None:
        """Render the current room in the upper room panel.

        If a transition was signalled by :meth:`signal_transition`, performs
        the fade-to-black before re-drawing both visible panels.
        """
        if self._pending_transition:
            self._pending_transition = False
            self._fade_transition()
        room_view = self._current_room_view()
        if room_view is None:
            return

        inner_w = self._panel_inner_width()
        lines = build_room_lines(room_view, inner_w)
        self._render_panel(
            self._room_win,
            UI["ui_labels"]["panel_room"],
            lines,
            height=self._room_h,
            attr_resolver=room_attr,
        )
        self._refresh_log()
        self._refresh_header()

    # ── input ──────────────────────────────────────────────────────────────────

    def _get_input(self) -> str:
        """Draw the prompt in the input bar, read one line of player input, and return it.

        Reads characters through curses key handling so arrow keys and other
        function keys do not spill raw escape sequences like ``^[[B`` into the
        command prompt.

        Returns
        -------
        str
            The raw input string (stripped), or ``""`` on any error.
        """
        win = self._input_win
        if win is None or self.state.game_over:
            return ""
        prompt_attr = color_attr(
            self._supports_color(),
            COLOR_PROMPT,
            fallback=curses.A_REVERSE,
            bold=True,
        )
        max_input_len = min(78, max(1, self._w - 4))

        def _redraw(buffer: str) -> None:
            """Redraw the prompt bar with the current buffered input."""
            """Redraw the prompt bar with the current buffered input."""
            win.erase()
            try:
                win.addstr(0, 0, "> ", prompt_attr)
                if buffer:
                    win.addstr(0, 2, truncate_for_display(buffer, max_input_len))
            except curses.error:
                pass
            win.refresh()

        _redraw("")
        try:
            win.keypad(True)
        except curses.error:
            pass
        try:
            win.timeout(1000)
        except curses.error:
            pass

        chars: list[str] = []
        try:
            while True:
                try:
                    key = win.get_wch()
                except curses.error as error:
                    if str(error) == "no input":
                        self._refresh_header()
                        if self.state.game_over:
                            return ""
                        continue
                    return ""
                if key == curses.KEY_ENTER or key in ("\n", "\r"):
                    break
                if key == curses.KEY_BACKSPACE or key in ("\b", "\x7f"):
                    if chars:
                        chars.pop()
                    _redraw("".join(chars))
                    continue
                if (
                    isinstance(key, str)
                    and key.isprintable()
                    and len(chars) < max_input_len
                ):
                    chars.append(key)
                    _redraw("".join(chars))
        except Exception:
            return ""
        finally:
            try:
                win.timeout(-1)
            except curses.error:
                pass
        return "".join(chars).strip()

    # ── end screen override ────────────────────────────────────────────────────

    def _handle_end(self) -> None:
        """Render a dedicated end screen and wait for Enter to replay or any other key to exit."""
        end_lines = self._end_lines()
        if end_lines is None:
            return

        room = self.current_room()
        room_panel_lines: list[tuple[str, str]] = []
        if room is not None:
            room_panel_lines.append(("title", room.name))
            room_panel_lines.append(("blank", ""))

        room_inner_w = self._panel_inner_width()
        for line in end_lines:
            wrapped = textwrap.wrap(line, room_inner_w) if line else []
            room_panel_lines.extend(("body", part) for part in (wrapped or [""]))

        prompt = UI["end"]["press_enter_to_replay"]
        log_panel_lines = [
            ("response", part) for part in (textwrap.wrap(prompt, room_inner_w) or [""])
        ]

        self._render_panel(
            self._room_win,
            UI["ui_labels"]["panel_room"],
            room_panel_lines,
            height=self._room_h,
            attr_resolver=room_attr,
        )
        self._render_panel(
            self._log_win,
            UI["ui_labels"]["panel_log"],
            log_panel_lines,
            height=self._log_h,
            attr_resolver=log_attr,
        )
        self._refresh_header()

        if self._input_win:
            self._input_win.erase()
            self._input_win.refresh()
        try:
            curses.noecho()
            curses.flushinp()
        except curses.error:
            pass
        wait_win = self._input_win or self._stdscr
        if wait_win:
            try:
                key = wait_win.getch()
                self.state.replay_requested = key in (
                    curses.KEY_ENTER,
                    ord("\n"),
                    ord("\r"),
                )
            except curses.error:
                pass
