"""Composition root for Final Exam: Room 314."""

from __future__ import annotations

from game import load_yaml_data

from game.commands.player_commands import build_commands
from game.engine.engine import GameEngine
from game.event import load_events
from game.state import GameState
from game.world import build_world

UI = load_yaml_data("commands.yaml")["responses"]


def main() -> None:
    """Build the game world and start the default engine.

    Command-line argument parsing is kept in this composition root so the
    repository's public entry point remains ``python -m game.main``.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="main",
        description=UI["cli"]["description"],
    )
    parser.add_argument(
        "--no-curses",
        action="store_true",
        help=UI["cli"]["no_curses_help"],
    )
    args = parser.parse_args()

    replay_requested = False
    while True:
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
            from game.engine.curses_engine import CursesEngine

            engine = CursesEngine(rooms, state, registry, event_queue)

        engine_ref[0] = engine
        engine.run()
        replay_requested = engine.state.replay_requested is True
        if not replay_requested:
            break


if __name__ == "__main__":
    main()
