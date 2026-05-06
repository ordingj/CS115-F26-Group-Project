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

from game.engine import GameEngine
from game.puzzle import step1_clue_text

# Fraction of the terminal height devoted to the room panel.
_ROOM_RATIO = 0.40


class CursesEngine(GameEngine):
    """GameEngine subclass that renders in a curses split-pane layout."""

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """Forward all arguments to :class:`~game.engine.GameEngine`.

        Uses ``*args``/``**kwargs`` forwarding to avoid duplicating the parent
        class parameter list — update :class:`~game.engine.GameEngine` and this
        subclass stays in sync automatically.
        """
        super().__init__(*args, **kwargs)
        self._log_lines: list[str] = []
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
        """Start the game inside a curses wrapper for automatic cleanup."""
        curses.wrapper(self._curses_run)

    # ── curses run loop ────────────────────────────────────────────────────────

    def _curses_run(self, stdscr: curses.window) -> None:
        """Main game loop executed inside the curses wrapper.

        Called by :meth:`run` via :func:`curses.wrapper`; *stdscr* is the
        full-screen window provided by curses.
        """
        self._stdscr = stdscr
        curses.curs_set(1)
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)  # room name
            curses.init_pair(2, curses.COLOR_YELLOW, -1)  # event markers (reserved)
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)  # header bar

        self._setup_windows()

        # Intro messages logged before the first room description.
        self._log("FINAL EXAM: ROOM 314")
        self._log("Your final exam starts in 10 minutes. Find Room 314.")
        self._log("Type HELP for a list of commands.")
        self._log("")

        self.describe_current_room()

        while not self.state.game_over:
            for msg in self.event_queue.tick(self.state):
                self._log("[!] " + msg)
            self._refresh_header()

            raw = self._get_input()
            if not raw:
                continue

            self._log("> " + raw)
            command = self.parser.parse(raw)
            result = self.registry.dispatch(command, self.state)
            if result:
                self._log(result)

            self.state.tick()

        self._handle_end()

    # ── window setup ───────────────────────────────────────────────────────────

    def _setup_windows(self) -> None:
        """Create and size the four curses sub-windows from the current terminal dimensions."""
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

        self._refresh_header()

    # ── display helpers ────────────────────────────────────────────────────────

    def _refresh_header(self) -> None:
        """Redraw the top title/time bar."""
        win = self._header_win
        if win is None:
            return
        win.erase()
        title = "  FINAL EXAM: ROOM 314"
        time_str = "Time: " + self.state.formatted_time() + "  "
        gap = max(0, self._w - len(title) - len(time_str))
        line = title + " " * gap + time_str
        try:
            attr = (
                curses.color_pair(3) | curses.A_BOLD
                if curses.has_colors()
                else curses.A_REVERSE
            )
            win.addstr(0, 0, line[: self._w], attr)
        except curses.error:
            pass
        win.refresh()

    def _log(self, msg: str) -> None:
        """Append a message to the log panel, wrapping long lines."""
        wrapped = textwrap.wrap(msg, max(1, self._w - 1)) if msg.strip() else [""]
        self._log_lines.extend(wrapped)
        self._refresh_log()

    def _refresh_log(self) -> None:
        """Re-render the scrolling log panel, showing the most recent lines."""
        win = self._log_win
        if win is None:
            return
        win.erase()
        visible = self._log_lines[-self._log_h :]
        for row, line in enumerate(visible):
            if row >= self._log_h:
                break
            try:
                win.addstr(row, 0, line[: self._w - 1])
            except curses.error:
                pass
        win.refresh()

    # ── room display override ──────────────────────────────────────────────────

    def describe_current_room(self) -> None:
        """Render the current room in the upper panel."""
        room = self.current_room()
        if room is None:
            return

        inner_w = max(1, self._w - 4)  # 2 border cols + 2 padding cols
        lines: list[str] = []
        lines.append(f"[ {room.name} ]")
        lines.append("")
        lines.extend(textwrap.wrap(room.description, inner_w))

        # Puzzle-specific inline hints (mirrors the plain-text engine logic).
        if room.room_id == "intersection_4way":
            clue = step1_clue_text(self.state)
            if clue:
                lines.append("")
                lines.extend(textwrap.wrap(clue, inner_w))
        elif room.room_id == "bathroom":
            status = self._bathroom_status()
            if status:
                lines.append("")
                lines.extend(textwrap.wrap(status, inner_w))

        exits = [d for d, dest in room.exits.items() if dest is not None]
        if exits:
            lines.append("")
            lines.append(f"Exits: {', '.join(exits)}")
        if room.items:
            lines.append(f"You see: {', '.join(room.items.values())}")

        win = self._room_win
        if win is None:
            return
        win.erase()
        try:
            win.border()
        except curses.error:
            pass
        for row, line in enumerate(lines):
            if row >= self._room_h - 2:
                break
            try:
                attr = curses.A_NORMAL
                if row == 0:
                    attr = (
                        curses.color_pair(1) | curses.A_BOLD
                        if curses.has_colors()
                        else curses.A_BOLD
                    )
                win.addstr(row + 1, 2, line[:inner_w], attr)
            except curses.error:
                pass
        win.refresh()
        self._refresh_header()

    # ── input ──────────────────────────────────────────────────────────────────

    def _get_input(self) -> str:
        """Draw the prompt, read one line of player input, and return it."""
        win = self._input_win
        if win is None:
            return ""
        win.erase()
        try:
            win.addstr(0, 0, "> ")
        except curses.error:
            pass
        win.refresh()
        curses.echo()
        curses.nocbreak()
        try:
            raw = (
                win.getstr(0, 2, min(78, max(1, self._w - 4)))
                .decode("utf-8", errors="replace")
                .strip()
            )
        except Exception:
            raw = ""
        finally:
            curses.noecho()
            curses.cbreak()
        return raw

    # ── end screen override ────────────────────────────────────────────────────

    def _handle_end(self) -> None:
        """Log the appropriate end screen and wait for a keypress before exiting."""
        if self.state.won and self.state.time_remaining >= 300:
            end_lines = [
                "YOU MADE IT TO ROOM 314 \u2014 FIVE MINUTES EARLY.",
                "The room is empty. The desks are empty. The exam",
                "schedule on the door says the final isn't until TOMORROW.",
                "You sit down anyway. You are very tired.",
            ]
        elif self.state.won:
            end_lines = [
                "YOU MADE IT TO ROOM 314!",
                "The exam is already in progress, but you're here.",
            ]
        elif self.state.quit:
            # Farewell message was already logged by handle_quit; just confirm exit.
            end_lines = []
        else:
            end_lines = [
                "TIME'S UP.",
                "You hear the distant sound of exam papers being collected.",
                "Game over.",
            ]

        self._log("")
        self._log("=" * max(1, self._w - 2))
        for line in end_lines:
            self._log(line)
        self._log("=" * max(1, self._w - 2))
        self._log("Press any key to exit.")

        if self._input_win:
            self._input_win.erase()
            self._input_win.refresh()
        curses.noecho()
        if self._stdscr:
            self._stdscr.getch()
