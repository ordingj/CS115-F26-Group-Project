"""GameEngine – main game loop and room rendering."""

from __future__ import annotations

from typing import Optional

from game.command import CommandParser, CommandRegistry
from game.event import EventQueue
from game.puzzle import step1_clue_text
from game.room import Room
from game.state import GameState


class GameEngine:
    """Orchestrates rooms, commands, events, and the main game loop."""

    def __init__(
        self,
        rooms: dict[str, Room],
        state: GameState,
        registry: CommandRegistry,
        event_queue: EventQueue,
    ) -> None:
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
            # Fire any pending events (time warnings, ambient flavour, etc.).
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
            if room.attributes.get("sink_running", False):
                print("\nThe motion-sensor sink is running. (Try: WASH HANDS)")
            elif self.state.has_flag("step2_hands_washed"):
                print("\nThe sink is off. Your hands are clean.")
        exits = [d for d, dest in room.exits.items() if dest is not None]
        if exits:
            print(f"Exits: {', '.join(exits)}")
        if room.items:
            print(f"You see: {', '.join(room.items.values())}")
        print(f"Time remaining: {self.state.formatted_time()}")

    # ── private helpers ────────────────────────────────────────────────────────

    def _print_intro(self) -> None:
        print("\n" + "=" * 60)
        print("  FINAL EXAM: ROOM 314")
        print("=" * 60)
        print("Your final exam starts in 10 minutes.")
        print("The problem: you can't find the classroom.\n")
        print("Your teacher's voice echoes: \"The final will be in Room 314.")
        print("You really don't want to be late.\"\n")

    def _handle_end(self) -> None:
        if self.state.won:
            print("\n" + "=" * 60)
            print("  YOU MADE IT TO ROOM 314!")
            print("  The exam is already in progress, but you're here.")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("  TIME'S UP.")
            print("  You hear the distant sound of exam papers being collected.")
            print("  Game over.")
            print("=" * 60)
