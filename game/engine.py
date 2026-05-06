"""GameEngine – main game loop and room rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from game.command import CommandParser, CommandRegistry
from game.event import EventQueue
from game.puzzle import step1_clue_text
from game.room import Room
from game.state import GameState

_UI: dict = yaml.safe_load(
    (Path(__file__).parent.parent / "data" / "commands.yaml").read_text(encoding="utf-8")
)["responses"]


class GameEngine:
    """Orchestrates rooms, commands, events, and the main game loop."""

    def __init__(
        self,
        rooms: dict[str, Room],
        state: GameState,
        registry: CommandRegistry,
        event_queue: EventQueue,
    ) -> None:
        """Initialise the engine with the full game world and a fresh state.

        Args:
            rooms:       Mapping of room_id -> :class:`~game.room.Room` built by
                         :func:`~game.world.build_world`.
            state:       The :class:`~game.state.GameState` for this session.
            registry:    Command registry populated by
                         :func:`main.build_commands`.
            event_queue: Ambient event queue built by
                         :func:`main.build_events`.
        """
        self.rooms = rooms
        self.state = state
        self.registry = registry
        self.event_queue = event_queue
        self.parser = CommandParser()

    # ── public API ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Start and run the game until a terminal condition is reached."""
        self._print_intro()
        self.describe_current_room()

        while not self.state.game_over:
            # Fire any pending events (time warnings, ambient flavor, etc.).
            for msg in self.event_queue.tick(self.state):
                print(f"\n{msg}")

            raw = input("\n> ").strip()
            if not raw:
                continue

            command = self.parser.parse(raw)
            result = self.registry.dispatch(command, self.state)
            if result:
                print(f"\n{result}")

            # Advance time after every non-empty command.
            self.state.tick()

        self._handle_end()

    def current_room(self) -> Optional[Room]:
        """Return the :class:`~game.room.Room` the player is currently in, or None."""
        return self.rooms.get(self.state.current_room_id)

    def describe_current_room(self) -> None:
        """Print the current room's name, description, exits, and visible items."""
        room = self.current_room()
        if room is None:
            return
        print(f"\n[ {room.name} ]")
        print(room.description)
        # Inject Step 1 clue when player is at the 4-way intersection.
        if room.room_id == "intersection_4way":
            clue = step1_clue_text(self.state)
            if clue:
                print(f"\n{clue}")
        # Show sink status in bathroom.
        elif room.room_id == "bathroom":
            status = self._bathroom_status()
            if status:
                print(f"\n{status}")
        # Show ambient janitor lyric clue (grows with urgency).
        elif room.room_id == "hallway_janitor":
            hint = self._janitor_hint()
            if hint:
                print(f"\n{hint}")
        exits = [d for d, dest in room.exits.items() if dest is not None]
        if exits:
            print(f"Exits: {', '.join(exits)}")
        if room.items:
            print(f"You see: {', '.join(room.items.values())}")
        print(f"Time remaining: {self.state.formatted_time()}")

    # ── private helpers ────────────────────────────────────────────────────────

    def _bathroom_status(self) -> str:
        """Return the current sink/handwashing status line for the bathroom room.

        Returns an empty string when the bathroom is not the current room or
        when no status line is appropriate.
        """
        room = self.current_room()
        if room is None or room.room_id != "bathroom":
            return ""
        phase = room.attributes.get("wash_phase", 0)
        running = room.attributes.get("sink_running", False)
        bs = _UI["bathroom_status"]
        if self.state.has_flag("step2_hands_washed"):
            return bs["clean"]
        if running and phase == 0:
            if room.attributes.get("soap_applied"):
                return bs["soapy"]
            return bs["soap_needed"]
        if not running and phase == 1:
            return bs["water_cut"]
        if running and phase == 2:
            return bs["water_back"]
        if running and phase == 3:
            return bs["final_rinse"]
        return ""

    def _janitor_hint(self) -> str:
        """Return an ambient chorus snippet for the janitor hallway, scaled to urgency.

        Shows one lyric line when time is plentiful, two around the midpoint,
        and all remaining lines in the final stretch, so the clue becomes
        easier to use as pressure mounts.
        """
        room = self.current_room()
        if room is None or room.room_id != "hallway_janitor":
            return ""
        chorus = self.state.active_clues.get("step3_song_chorus", "")
        if not chorus:
            return ""
        all_lines = chorus.strip().splitlines()
        t = self.state.time_remaining
        count = 1 if t > 300 else (2 if t > 150 else len(all_lines))
        shown = all_lines[:count]
        indented = "\n".join(f"  {line}" for line in shown)
        return _UI["ambient"]["janitor_hint_prefix"] + "\n" + indented

    def _print_intro(self) -> None:
        """Print the one-time opening title card and story hook."""
        intro = _UI["intro"]
        print("\n" + "=" * 60)
        print(f"  {intro['title']}")
        print("=" * 60)
        print(intro["opening"])
        print(intro["problem"] + "\n")
        print(intro["teacher"] + "\n")

    def _handle_end(self) -> None:
        """Print the appropriate end screen based on final game state."""
        end = _UI["end"]
        if self.state.won and self.state.time_remaining >= 300:
            key = "won_early"
        elif self.state.won:
            key = "won"
        elif self.state.quit:
            return  # farewell already printed by handle_quit
        else:
            key = "lost"
        print("\n" + "=" * 60)
        for line in end[key].splitlines():
            print(f"  {line}")
        print("=" * 60)
