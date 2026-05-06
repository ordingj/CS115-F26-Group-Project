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
            phase = room.attributes.get("wash_phase", 0)
            running = room.attributes.get("sink_running", False)
            if self.state.has_flag("step2_hands_washed"):
                print("\nThe sink is off. Your hands are clean.")
            elif running and phase == 0:
                print("\nThe motion-sensor sink is running. (Try: RINSE HANDS)")
            elif not running and phase == 1:
                print(
                    "\nThe water cut off. Your hands are still soapy. "
                    "(Try: STOP to pull your hands back)"
                )
            elif running and phase == 2:
                print(
                    "\nThe water came back on. Quick — rinse again before it cuts off. "
                    "(Try: RINSE HANDS)"
                )
            elif running and phase == 3:
                print("\nThe water is still running. Your hands are clean. (Try: STOP)")
        exits = [d for d, dest in room.exits.items() if dest is not None]
        if exits:
            print(f"Exits: {', '.join(exits)}")
        if room.items:
            print(f"You see: {', '.join(room.items.values())}")
        print(f"Time remaining: {self.state.formatted_time()}")

    # ── private helpers ────────────────────────────────────────────────────────

    def _print_intro(self) -> None:
        """Print the one-time opening title card and story hook."""
        print("\n" + "=" * 60)
        print("  FINAL EXAM: ROOM 314")
        print("=" * 60)
        print("Your final exam starts in 10 minutes.")
        print("The problem: you can't find the classroom.\n")
        print("Your teacher's voice echoes: \"The final will be in Room 314.")
        print("You really don't want to be late.\"\n")

    def _handle_end(self) -> None:
        """Print the appropriate end screen based on final game state."""
        if self.state.won and self.state.time_remaining >= 300:
            print("\n" + "=" * 60)
            print("  YOU MADE IT TO ROOM 314. FIVE MINUTES EARLY.")
            print("  The room is empty. The desks are empty. The exam")
            print("  schedule on the door says the final isn't until")
            print("  TOMORROW. You sit down anyway. You are very tired.")
            print("=" * 60)
        elif self.state.won:
            print("\n" + "=" * 60)
            print("  YOU MADE IT TO ROOM 314!")
            print("  The exam is already in progress, but you're here.")
            print("=" * 60)
        elif self.state.quit:
            pass  # farewell already printed by handle_quit
        else:
            print("\n" + "=" * 60)
            print("  TIME'S UP.")
            print("  You hear the distant sound of exam papers being collected.")
            print("  Game over.")
            print("=" * 60)
