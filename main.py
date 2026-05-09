"""Composition root for Final Exam: Room 314."""

from __future__ import annotations
from game.engine import GameEngine
from game.event import load_events
from game.player_commands import build_commands
from game.state import GameState
from game.world import build_world


def main() -> None:
    """Build the game world and start the default engine.

    Command-line argument parsing is kept in this composition root so the
    repository's public entry point remains ``python main.py``.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="main",
        description="Final Exam: Room 314 – a text adventure",
    )
    parser.add_argument(
        "--no-curses",
        action="store_true",
        help="Run in plain-text mode (no curses UI)",
    )
    args = parser.parse_args()

    rooms = build_world()
    state = GameState(current_room_id="lobby")
    event_queue = load_events()

    # One-element list gives command handlers a mutable reference to the engine
    # without a circular dependency.
    engine_ref: list[GameEngine | None] = [None]
    registry = build_commands(engine_ref)

    if args.no_curses:
        engine: GameEngine = GameEngine(rooms, state, registry, event_queue)
    else:
        from game.curses_engine import CursesEngine

        engine = CursesEngine(rooms, state, registry, event_queue)

    engine_ref[0] = engine
    engine.run()


if __name__ == "__main__":
    main()
