"""Entry point – Final Exam: Room 314."""

from __future__ import annotations

from game.command import CommandRegistry
from game.engine import GameEngine
from game.event import Event, EventQueue
from game.puzzle import step1_is_correct, step1_roll
from game.state import GameState
from game.world import build_world


# ── command builder ────────────────────────────────────────────────────────────


def build_commands(engine_ref: list[GameEngine | None]) -> CommandRegistry:
    """Register all player-facing commands and return the registry.

    engine_ref is a one-element list so handlers can reach the live engine
    without a circular import (the engine is not created until after the
    registry is built).
    """
    registry = CommandRegistry()

    # ── movement ───────────────────────────────────────────────────────────────
    def handle_move(verb: str, target: str | None, state: GameState) -> str:
        engine = engine_ref[0]
        if engine is None:
            return "Error: engine not initialised."
        room = engine.current_room()
        if room is None:
            return "You are nowhere."
        if verb not in room.exits:
            return "You can't go that way."
        destination_id = room.exits[verb]
        if destination_id is None:
            return "That way is blocked."

        # ── Step 1: 4-way intersection puzzle ─────────────────────────────────
        if room.room_id == "intersection_4way":
            if not step1_is_correct(verb, state):
                # Wrong way — bounce through a flavour room then back.
                state.wrong_turns += 1
                state.set_flag("step1_wrong_way", True)
                state.current_room_id = destination_id
                engine.describe_current_room()
                return (
                    "\nSomething feels wrong. The hallway ahead looks exactly like "
                    "one you've already walked. You think you've been here before."
                )
            # Correct direction — advance puzzle state.
            state.puzzle_step = 1
            state.set_flag("step1_solved", True)

        state.current_room_id = destination_id

        # Roll a fresh Step 1 clue any time the player (re-)enters the 4-way.
        if destination_id == "intersection_4way":
            step1_roll(state)
            # Wire the correct exit to the 3-way intersection; others loop back
            # through flavour rooms (wrong-way logic handles the bounce).
            correct_dir = state.active_clues["step1_correct_dir"]
            intersection = engine.rooms["intersection_4way"]
            for d in ("forward", "left", "right"):
                intersection.exits[d] = "intersection_3way" if d == correct_dir else "flavour_copy_room"

        engine.describe_current_room()
        return ""

    for direction in ("forward", "back", "left", "right"):
        registry.register(direction, handle_move)

    # ── look / examine ─────────────────────────────────────────────────────────
    def handle_look(verb: str, target: str | None, state: GameState) -> str:
        engine = engine_ref[0]
        if engine:
            engine.describe_current_room()
        return ""

    registry.register("look", handle_look)
    registry.register("examine", handle_look)

    # ── check watch ────────────────────────────────────────────────────────────
    def handle_check(verb: str, target: str | None, state: GameState) -> str:
        if target in (None, "watch", "time"):
            return f"Your watch reads {state.formatted_time()} remaining."
        return f"You check the {target}, but find nothing useful."

    registry.register("check", handle_check)

    # ── read ───────────────────────────────────────────────────────────────────
    def handle_read(verb: str, target: str | None, state: GameState) -> str:
        if target is None:
            return "Read what?"
        engine = engine_ref[0]
        room = engine.current_room() if engine else None
        if room and target in room.items:
            # Placeholder: room-specific read logic goes here.
            return (
                f"You read the {room.items[target]}, but the text is hard to make out."
            )
        return f"There is no '{target}' here to read."

    registry.register("read", handle_read)

    # ── open ───────────────────────────────────────────────────────────────────
    def handle_open(verb: str, target: str | None, state: GameState) -> str:
        if target is None:
            return "Open what?"
        return f"You try to open the {target}, but it won't budge."

    registry.register("open", handle_open)

    # ── knock ──────────────────────────────────────────────────────────────────
    def handle_knock(verb: str, target: str | None, state: GameState) -> str:
        if target is None:
            return "Knock on what?"
        return f"You knock on the {target}. No answer."

    registry.register("knock", handle_knock)

    # ── listen ─────────────────────────────────────────────────────────────────
    def handle_listen(verb: str, target: str | None, state: GameState) -> str:
        return "You listen carefully. The building hums with an uneasy silence."

    registry.register("listen", handle_listen)

    # ── help ───────────────────────────────────────────────────────────────────
    def handle_help(verb: str, target: str | None, state: GameState) -> str:
        engine = engine_ref[0]
        verbs = engine.registry.known_verbs() if engine else []
        return "Commands: " + ", ".join(verbs)

    registry.register("help", handle_help)

    # ── quit ───────────────────────────────────────────────────────────────────
    def handle_quit(verb: str, target: str | None, state: GameState) -> str:
        state.game_over = True
        return "You give up and head home. Game over."

    registry.register("quit", handle_quit)

    return registry


# ── event builder ──────────────────────────────────────────────────────────────


def build_events() -> EventQueue:
    """Register ambient and time-based narrative events."""
    queue = EventQueue()

    queue.register(
        Event(
            event_id="time_warning_5min",
            message="Your phone buzzes. A calendar reminder: exam starts in 5 minutes.",
            condition=lambda s: 285 < s.time_remaining <= 300,
        )
    )
    queue.register(
        Event(
            event_id="time_warning_2min",
            message=(
                "You are standing underneath a vent that is blasting cold air. "
                "Two minutes left."
            ),
            condition=lambda s: 105 < s.time_remaining <= 120,
        )
    )
    queue.register(
        Event(
            event_id="ominous_footsteps",
            message="You hear footsteps behind you. When you turn around, no one is there.",
            condition=lambda s: s.move_count == 5,
        )
    )
    queue.register(
        Event(
            event_id="ominous_watched",
            message="You feel like you're being watched.",
            condition=lambda s: s.move_count == 10,
        )
    )
    queue.register(
        Event(
            event_id="ominous_whisper",
            message="You hear a whisper, but can't make out the words.",
            condition=lambda s: s.move_count == 15,
        )
    )

    return queue


# ── entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    rooms = build_world()
    state = GameState(current_room_id="lobby")
    event_queue = build_events()

    # One-element list gives command handlers a mutable reference to the engine
    # without a circular dependency.
    engine_ref: list[GameEngine | None] = [None]
    registry = build_commands(engine_ref)

    engine = GameEngine(rooms, state, registry, event_queue)
    engine_ref[0] = engine

    engine.run()


if __name__ == "__main__":
    main()
