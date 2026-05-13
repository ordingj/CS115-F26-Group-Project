"""Shared formatting and panel-rendering helpers for the curses UI.

This module is imported by both
:class:`~game.engine.curses_engine.CursesEngine` and its test helpers. All
curses colour-pair IDs are defined here so they stay centralised and can be
referenced symbolically (e.g. ``COLOR_EVENT``) instead of by magic number.
"""

from __future__ import annotations

import curses
import textwrap
import unicodedata
from collections.abc import Callable

from game.engine.engine import CurrentRoomView, UI

PANEL_PAD = 2

COLOR_ROOM_TITLE = 1
COLOR_EVENT = 2
COLOR_HEADER = 3
COLOR_COMMAND = 4
COLOR_SECTION = 5
COLOR_CLUE = 6
COLOR_EXIT = 7
COLOR_ITEM = 8
COLOR_SYSTEM = 9
COLOR_PROMPT = 10
COLOR_HEADER_WARNING = 11
COLOR_HEADER_DANGER = 12

_DOUBLE_WIDTH_EAST_ASIAN_WIDTHS = frozenset({"A", "F", "W"})


def init_colors() -> None:
    """Initialise the curses colour pairs used by the split-pane UI.

    Colour pair IDs correspond to the module-level ``COLOR_*`` constants.
    Each pair is ``(foreground, background)`` where ``-1`` means the
    terminal's default colour.
    """
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(COLOR_ROOM_TITLE, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_EVENT, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_HEADER, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(COLOR_COMMAND, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_SECTION, curses.COLOR_BLUE, -1)
    curses.init_pair(COLOR_CLUE, curses.COLOR_MAGENTA, -1)
    curses.init_pair(COLOR_EXIT, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_ITEM, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_SYSTEM, curses.COLOR_BLUE, -1)
    curses.init_pair(COLOR_PROMPT, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(COLOR_HEADER_WARNING, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(COLOR_HEADER_DANGER, curses.COLOR_WHITE, curses.COLOR_RED)


def _cell_width(char: str) -> int:
    """Return the terminal cell width for one character.

    Parameters
    ----------
    char : str
        Single character to measure.

    Returns
    -------
    int
        Number of terminal columns the character may occupy.

    Notes
    -----
    Ambiguous-width glyphs are treated as double-width on purpose. Some
    terminals render punctuation such as em dashes that way, and the curses
    renderer should clip conservatively instead of risking a dropped line.
    """
    if not char or unicodedata.combining(char):
        return 0
    if unicodedata.category(char).startswith("C"):
        return 0
    if unicodedata.east_asian_width(char) in _DOUBLE_WIDTH_EAST_ASIAN_WIDTHS:
        return 2
    return 1


def truncate_for_display(text: str, width: int) -> str:
    """Return *text* trimmed to fit within *width* terminal cells.

    Parameters
    ----------
    text : str
        Single-line text destined for ``curses.addstr``.
    width : int
        Maximum terminal cell width available.

    Returns
    -------
    str
        Text clipped so it never exceeds the requested cell width.
    """
    if width <= 0:
        return ""

    cells = 0
    clipped: list[str] = []
    for char in text:
        char_width = _cell_width(char)
        if cells + char_width > width:
            break
        clipped.append(char)
        cells += char_width
    return "".join(clipped).rstrip()


def build_system_line_set() -> set[str]:
    """Return a set of log-panel lines that should render as UI/system copy.

    Lines in this set are classified as ``"system"`` style by
    :func:`classify_log_line` so they receive a distinct colour (blue)
    instead of the default response colour.

    Returns
    -------
    set[str]
        Static strings drawn from ``commands.yaml`` intro and end sections.
    """
    intro = UI["intro"]
    end = UI["end"]
    lines = {
        intro["title"],
        intro["curses_subtitle"],
        intro["help_hint"],
        end["press_enter_to_replay"],
    }
    art = intro.get("ascii_art", "")
    if art:
        lines.update(line for line in art.splitlines() if line)
    for key in ("won_early", "won", "lost"):
        lines.update(line for line in end[key].splitlines() if line)
    return lines


def classify_log_line(line: str, system_lines: set[str]) -> str:
    """Classify a log line so the renderer can colour it consistently.

    Parameters
    ----------
    line : str
        A single line as stored in ``_log_lines`` (may include wrapping
        indentation but not a trailing newline).
    system_lines : set[str]
        Pre-built set of known UI/system strings from :func:`build_system_line_set`.

    Returns
    -------
    str
        One of: ``"blank"``, ``"divider"``, ``"system"``, ``"command"``,
        ``"event"``, or ``"response"``.
    """
    stripped = line.strip()
    if not stripped:
        return "blank"
    if set(stripped) == {"="}:
        return "divider"
    if line in system_lines:
        return "system"
    if line.startswith("> "):
        return "command"
    return "response"


def color_attr(
    supports_color: bool,
    pair_id: int,
    *,
    fallback: int = curses.A_NORMAL,
    bold: bool = False,
    dim: bool = False,
) -> int:
    """Build a curses attribute integer, degrading gracefully when colour is off.

    Parameters
    ----------
    supports_color : bool
        Whether :func:`curses.has_colors` returned ``True`` for this session.
    pair_id : int
        Colour pair ID (one of the ``COLOR_*`` module constants).
    fallback : int, optional
        Attribute to use when colours are not available; defaults to
        :data:`curses.A_NORMAL`.
    bold : bool, optional
        OR in :data:`curses.A_BOLD` when ``True``.
    dim : bool, optional
        OR in :data:`curses.A_DIM` when ``True``.

    Returns
    -------
    int
        Curses attribute integer ready to pass to ``win.addstr``.
    """
    attr = fallback
    if supports_color:
        try:
            attr = curses.color_pair(pair_id)
        except curses.error:
            attr = fallback
    if bold:
        attr |= curses.A_BOLD
    if dim:
        attr |= curses.A_DIM
    return attr


_StyleAttrConfig = tuple[int, int, bool, bool]

_LOG_STYLE_ATTRS: dict[str, _StyleAttrConfig] = {
    "event": (COLOR_EVENT, curses.A_NORMAL, True, False),
    "command": (COLOR_COMMAND, curses.A_NORMAL, True, False),
    "system": (COLOR_SYSTEM, curses.A_NORMAL, True, False),
    "divider": (COLOR_SYSTEM, curses.A_NORMAL, False, True),
}

_ROOM_STYLE_ATTRS: dict[str, _StyleAttrConfig] = {
    "title": (COLOR_ROOM_TITLE, curses.A_BOLD, True, False),
    "section": (COLOR_SECTION, curses.A_BOLD, True, False),
    "clue": (COLOR_CLUE, curses.A_NORMAL, False, False),
    "exit": (COLOR_COMMAND, curses.A_NORMAL, True, False),
    "item": (COLOR_ITEM, curses.A_NORMAL, False, False),
}


def _style_attr(
    style: str, supports_color: bool, style_attrs: dict[str, _StyleAttrConfig]
) -> int:
    """Return a curses attribute from one style-to-attribute lookup table.

    Parameters
    ----------
    style : str
        Style tag to look up.
    supports_color : bool
        Whether the terminal supports colour output.
    style_attrs : dict[str, _StyleAttrConfig]
        Mapping from style tag to ``color_attr`` parameters in the form
        ``(pair_id, fallback, bold, dim)``.

    Returns
    -------
    int
        Resolved curses attribute integer, or :data:`curses.A_NORMAL` when
        *style* is not present in the lookup table.
    """
    config = style_attrs.get(style)
    if config is None:
        return curses.A_NORMAL
    pair_id, fallback, bold, dim = config
    return color_attr(
        supports_color,
        pair_id,
        fallback=fallback,
        bold=bold,
        dim=dim,
    )


def log_attr(style: str, supports_color: bool) -> int:
    """Return the curses display attribute for a classified log panel line.

    Parameters
    ----------
    style : str
        Line style tag from :func:`classify_log_line`.
    supports_color : bool
        Whether the terminal supports colour output.

    Returns
    -------
    int
        Curses attribute integer.
    """
    return _style_attr(style, supports_color, _LOG_STYLE_ATTRS)


def room_attr(style: str, supports_color: bool) -> int:
    """Return the curses display attribute for a room-panel line.

    Parameters
    ----------
    style : str
        Line style tag assigned by :func:`build_room_lines`.
    supports_color : bool
        Whether the terminal supports colour output.

    Returns
    -------
    int
        Curses attribute integer.
    """
    return _style_attr(style, supports_color, _ROOM_STYLE_ATTRS)


def draw_panel_title(win: curses.window, title: str, supports_color: bool) -> None:
    """Render a small title label inside the top border of a boxed panel.

    Parameters
    ----------
    win : curses.window
        The panel window whose top border will receive the label.
    title : str
        Short label text (rendered as ``" TITLE "``).
    supports_color : bool
        Whether the terminal supports colour output.
    """
    _height, width = win.getmaxyx()
    label = truncate_for_display(f" {title} ", max(0, width - 4))
    if not label:
        return
    win.addstr(0, 2, label, color_attr(supports_color, COLOR_SECTION, bold=True))


def append_wrapped_lines(
    lines: list[tuple[str, str]],
    style: str,
    text: str,
    width: int,
    *,
    initial_indent: str = "",
    subsequent_indent: str = "",
) -> None:
    """Word-wrap *text* and append the resulting lines to *lines* with *style*.

    Parameters
    ----------
    lines : list[tuple[str, str]]
        The accumulator list of ``(style, text)`` pairs for the panel.
    style : str
        Style tag to attach to every generated line.
    text : str
        The text to wrap.  Multi-line strings are wrapped segment by segment.
    width : int
        Maximum character width per wrapped line.
    initial_indent : str, optional
        String prepended to the first line of each segment.
    subsequent_indent : str, optional
        String prepended to continuation lines of each segment.
    """
    for chunk in text.splitlines() or [text]:
        if not chunk:
            lines.append(("blank", ""))
            continue
        wrapped = textwrap.wrap(
            chunk,
            width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
        )
        lines.extend((style, line) for line in (wrapped or [initial_indent.rstrip()]))


def _append_room_section(
    lines: list[tuple[str, str]],
    label: str,
    style: str,
    text: str,
    width: int,
    *,
    initial_indent: str = "",
    subsequent_indent: str = "",
) -> None:
    """Append one optional room-panel section when *text* is non-empty.

    Parameters
    ----------
    lines : list[tuple[str, str]]
        The accumulator list of ``(style, text)`` pairs for the panel.
    label : str
        Section heading text from ``UI["ui_labels"]``.
    style : str
        Style tag to attach to wrapped content lines.
    text : str
        Section body text; when empty, nothing is appended.
    width : int
        Maximum character width per wrapped line.
    initial_indent : str, optional
        String prepended to the first line of each wrapped segment.
    subsequent_indent : str, optional
        String prepended to continuation lines of each wrapped segment.
    """
    if not text:
        return
    lines.append(("blank", ""))
    lines.append(("section", label))
    append_wrapped_lines(
        lines,
        style,
        text,
        width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
    )


def build_room_lines(room_view: CurrentRoomView, inner_w: int) -> list[tuple[str, str]]:
    """Build the styled ``(style, text)`` lines for the room panel.

    Parameters
    ----------
    room_view : CurrentRoomView
        Immutable snapshot of the current room's presentable data.
    inner_w : int
        Available text width inside the panel border.

    Returns
    -------
    list[tuple[str, str]]
        Ordered list of ``(style, text)`` pairs ready for
        :func:`render_boxed_panel`.
    """
    labels = UI["ui_labels"]
    lines: list[tuple[str, str]] = [
        ("title", room_view.name),
        ("blank", ""),
        ("section", labels["section_details"]),
    ]
    append_wrapped_lines(lines, "body", room_view.description, inner_w)
    if room_view.clue:
        lines.append(("blank", ""))
        append_wrapped_lines(lines, "clue", room_view.clue, inner_w)
    _append_room_section(
        lines,
        labels["section_exits"],
        "exit",
        ", ".join(room_view.exits),
        inner_w,
        initial_indent="  ",
        subsequent_indent="  ",
    )
    _append_room_section(
        lines,
        labels["section_items"],
        "item",
        ", ".join(room_view.items),
        inner_w,
        initial_indent="  ",
        subsequent_indent="  ",
    )

    return lines


def render_boxed_panel(
    win: curses.window | None,
    title: str,
    lines: list[tuple[str, str]],
    *,
    inner_w: int,
    height: int,
    supports_color: bool,
    attr_for_style: Callable[[str], int],
) -> None:
    """Render a list of styled lines inside one boxed curses panel window.

    Parameters
    ----------
    win : curses.window or None
        Target window.  When ``None`` the function is a safe no-op.
    title : str
        Panel title rendered inside the top border via :func:`draw_panel_title`.
    lines : list[tuple[str, str]]
        ``(style, text)`` pairs to display; the most recent ``height - 2``
        lines are shown (caller pre-slices for scrolling behaviour).
    inner_w : int
        Maximum character width per line (lines are truncated to this).
    height : int
        Total panel height in rows, including the 1-row borders.
    supports_color : bool
        Whether the terminal supports colour output.
    attr_for_style : Callable[[str], int]
        Maps a style tag string to a curses attribute integer.
    """
    if win is None:
        return
    win.erase()
    try:
        win.border()
        draw_panel_title(win, title, supports_color)
    except curses.error:
        pass

    for row, (style, line) in enumerate(lines):
        if row >= height - 2:
            break
        try:
            win.addstr(
                row + 1,
                PANEL_PAD,
                truncate_for_display(line, inner_w),
                attr_for_style(style),
            )
        except curses.error:
            pass
    win.refresh()
