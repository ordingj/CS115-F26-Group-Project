"""GameEngine – main game loop and room rendering for the plain-text UI.

This module provides :class:`GameEngine`, the primary game driver used when
curses is unavailable or the ``--no-curses`` flag is passed.  The curses
variaint (:class:`~game.curses_engine.CursesEngine`) inherits from it and
overrides only the presentation methods, keeping game-loop logic DRY.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from game import load_yaml_data
from game.puzzles.bathroom_view import bathroom_status_text
from game.commands.command import CommandParser, CommandRegistry
from game.event import EventQueue
from game.puzzles.intersection import intersection_description, step1_clue_text
from game.puzzles.janitor import janitor_text
from game.room import Room
from game.state import GameState

UI: dict[str, Any] = load_yaml_data("commands.yaml")["responses"]
_UI_LABELS: dict[str, str] = UI["ui_labels"]


@dataclass(frozen=True)
class CurrentRoomView:
    """Immutable snapshot of room-presentation data consumed by both UI layers.

    Computed once per describe cycle so the plain-text and curses renderers
    both show identical information without re-evaluating the game state twice.

    Attributes
    ----------
    name : str
        Room display name (e.g. ``"Building Lobby"``).
    description : str
        Full prose description of the room.
    clue : str
        Dynamic clue string (puzzle hint, bathroom status, janitor lyric), or
        an empty string when no clue applies.
    exits : tuple[str, ...]
        Direction names for all currently accessible exits.
    items : tuple[str, ...]
        Display names of items visible in the room.
    time_remaining : str
        Formatted time string from :meth:`~game.state.GameState.formatted_time`.
    """

    name: str
    description: str
    clue: str
    exits: tuple[str, ...]
    items: tuple[str, ...]
    time_remaining: str


class GameEngine:
    """Orchestrates rooms, commands, events, and the main game loop.

    This is the plain-text (``print``/``input``) variant of the engine.
    All game logic (state mutation, event firing, command dispatching) lives
    here; :class:`~game.curses_engine.CursesEngine` inherits and overrides
    only the I/O methods so logic stays in a single place.
    """

    def __init__(
        self,
        rooms: dict[str, Room],
        state: GameState,
        registry: CommandRegistry,
        event_queue: EventQueue,
    ) -> None:
        """Initialise the engine with the full game world and a fresh state.

        Parameters
        ----------
        rooms : dict[str, Room]
            Mapping of ``room_id`` → :class:`~game.room.Room` built by
            :func:`~game.world.build_world`.
        state : GameState
            Mutable game state for this session.
        registry : CommandRegistry
            Command registry populated by :func:`~game.player_commands.build_commands`.
        event_queue : EventQueue
            Ambient event queue built by :func:`~game.event.load_events`.
        """
        self.rooms = rooms
        self.state = state
        self.registry = registry
        self.event_queue = event_queue
        self.parser = CommandParser()

    # ── public API ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Start and run the game loop until a terminal condition is reached.

        The loop fires pending events, reads a command from the player,
        dispatches it, and ticks the clock.  It exits when
        ``state.game_over`` becomes ``True`` (timeout, win, or quit).
        """
        self._start_session()
        self._play_until_game_over()
        self._handle_end()

    def current_room(self) -> Room | None:
        """Return the :class:`~game.room.Room` the player is currently in.

        Returns
        -------
        Room or None
            The ``Room`` object for ``state.current_room_id``, or ``None``
            if the ID is somehow not in the rooms dict.
        """
        return self.rooms.get(self.state.current_room_id)

    def signal_transition(self) -> None:
        """Arm a visual room-transition effect before the next room description.

        The base (plain-text) implementation is a no-op.  Subclasses
        (e.g. :class:`~game.curses_engine.CursesEngine`) override this to
        trigger effects such as a fade-to-black between rooms.
        """

    def should_render_arrival_room(self) -> bool:
        """Return whether a committed move should redraw the destination room.

        The plain-text engine skips the redraw once an arrival hook has
        already ended the game so the run loop can go straight to the ending
        screen.  UI-specific subclasses can override this when they need to
        present the destination room before their dedicated end-screen flow.
        """
        return not self.state.game_over

    def describe_current_room(self) -> None:
        """Print the current room's name, description, exits, and visible items.

        Delegates to :meth:`_current_room_view` to gather data so the curses
        subclass can reuse the same view snapshot for its own rendering.
        """
        room_view = self._current_room_view()
        if room_view is None:
            return
        print(f"\n[ {room_view.name} ]")
        print(room_view.description)
        if room_view.clue:
            print(f"\n{room_view.clue}")
        if room_view.exits:
            print(_UI_LABELS["plain_exits_prefix"] + ", ".join(room_view.exits))
        if room_view.items:
            print(_UI_LABELS["plain_items_prefix"] + ", ".join(room_view.items))
        print(_UI_LABELS["plain_time_prefix"] + room_view.time_remaining)

    # ── private helpers ────────────────────────────────────────────────────────

    def _current_room_clue(self, room: Room) -> str:
        """Return the dynamic clue text for *room*, or ``""`` when none applies.

        Dispatches to the appropriate helper based on ``room.room_id``:
        puzzle clue for the 4-way intersection, wash status for the bathroom,
        and janitor hint for the janitor hallway.

        Parameters
        ----------
        room : Room
            The room to generate a clue for.

        Returns
        -------
        str
            Dynamic clue string, or an empty string.
        """
        if room.room_id == "intersection_4way":
            return step1_clue_text(self.state)
        if room.room_id == "bathroom":
            return bathroom_status_text(room, self.state, UI["bathroom_status"])
        if room.room_id == "hallway_janitor":
            return janitor_text(self.state, UI["ambient"]["janitor_hint_prefix"])
        return ""

    def _current_room_view(self) -> CurrentRoomView | None:
        """Build and return a :class:`CurrentRoomView` for the current room.

        Computing the view once and passing it to both the log panel and room
        panel prevents the two UI layers from evaluating state twice or
        showing inconsistent data.

        Returns
        -------
        CurrentRoomView or None
            Snapshot of the current room's presentable data, or ``None`` if
            ``state.current_room_id`` is not in the rooms dict.
        """
        room = self.current_room()
        if room is None:
            return None
        description = (
            intersection_description(room, self.state)
            if room.room_id == "intersection_4way"
            else room.description
        )
        return CurrentRoomView(
            name=room.name,
            description=description,
            clue=self._current_room_clue(room),
            exits=tuple(
                direction for direction, dest in room.exits.items() if dest is not None
            ),
            items=tuple(room.items.values()),
            time_remaining=self.state.formatted_time(),
        )

    def _intro_banner_lines(self) -> list[str]:
        """Return the intro banner lines, including optional ASCII art.

        Both the plain-text engine and the curses engine share the same
        banner source so both entry points stay visually consistent.

        Returns
        -------
        list[str]
            Lines to display in the opening title card, with the ASCII art
            (if configured) prepended before the title line.
        """
        intro = UI["intro"]
        lines: list[str] = []
        art = intro.get("ascii_art", "")
        if art:
            lines.extend(art.splitlines())
            lines.append("")
        lines.append(intro["title"])
        return lines

    def _print_framed_lines(self, lines: list[str]) -> None:
        """Print one bordered block of lines using the plain-text UI frame."""
        print("\n" + "=" * 60)
        for line in lines:
            if line:
                print(f"  {line}")
            else:
                print()
        print("=" * 60)

    def _print_intro(self) -> None:
        """Print the one-time opening title card and story-hook paragraphs."""
        intro = UI["intro"]
        self._print_framed_lines(self._intro_banner_lines())
        print(intro["opening"])
        print(intro["problem"] + "\n")
        print(intro["teacher"] + "\n")

    def _start_session(self) -> None:
        """Show the intro for this UI and render the starting room once."""
        self._print_intro()
        self.describe_current_room()

    def _emit_event(self, message: str) -> None:
        """Present one ambient event message in the active UI."""
        print(f"\n{message}")

    def _before_command_prompt(self) -> None:
        """Run any per-turn UI refresh needed before input is collected."""

    def _read_command(self) -> str:
        """Return one raw player command line for the active UI."""
        return input("\n> ").strip()

    def _echo_command(self, raw: str) -> None:
        """Optionally echo the raw player command in the active UI."""

    def _emit_command_result(self, result: str) -> None:
        """Present one command result string in the active UI."""
        print(f"\n{result}")

    def _play_until_game_over(self) -> None:
        """Run the shared event/input/dispatch/tick loop until the game ends."""
        while not self.state.game_over:
            for msg in self.event_queue.tick(self.state):
                self._emit_event(msg)

            self._before_command_prompt()
            raw = self._read_command()
            if not raw:
                continue

            self._echo_command(raw)
            command = self.parser.parse(raw)
            result = self.registry.dispatch(command, self.state)
            if result:
                self._emit_command_result(result)

            self.state.tick()

    def _end_lines(self) -> list[str] | None:
        """Return end-screen text lines, or ``None`` when quit handled the farewell.

        Returns
        -------
        list[str] or None
            Lines to print inside the end-screen border, or ``None`` if the
            player quit (the quit command already showed a goodbye message).
        """
        end = UI["end"]
        if self.state.quit:
            return None
        if self.state.won and self.state.time_remaining >= 300:
            return end["won_early"].splitlines()
        if self.state.won:
            return end["won"].splitlines()
        return end["lost"].splitlines()

    def _handle_end(self) -> None:
        """Print the appropriate end screen based on final game state."""
        lines = self._end_lines()
        if lines is None:
            return
        self._print_framed_lines(lines)
        replay_input = input(f"\n{UI['end']['press_enter_to_replay']} ")
        self.state.replay_requested = replay_input.strip() == ""
