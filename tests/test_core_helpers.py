"""Unit tests for command, state, and shared data helpers.

Covers :class:`~game.command.CommandParser`, :class:`~game.command.CommandRegistry`,
:class:`~game.state.GameState`, and :func:`~game.load_yaml_data`.
"""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import main as main_module
from game import load_yaml_data
from game.command import (
    Command,
    CommandParser,
    CommandRegistry,
    register_target_state_handler,
)
from game.state import GameState


class CommandParserTest(unittest.TestCase):
    """Verify raw input tokenisation."""

    def test_parse_normalises_case_and_target_spacing(self) -> None:
        """Verify that parse() lowercases the verb and collapses extra whitespace in the target."""
        parser = CommandParser()

        command = parser.parse("  ReAd   Detour   Sign  ")

        self.assertEqual(command, Command(verb="read", target="detour sign"))

    def test_parse_empty_input_returns_blank_verb(self) -> None:
        """Verify that whitespace-only input produces a Command with an empty verb and no target."""
        parser = CommandParser()

        command = parser.parse("   ")

        self.assertEqual(command, Command(verb="", target=None))


class CommandRegistryTest(unittest.TestCase):
    """Verify handler registration and fallback behaviour."""

    def test_dispatch_routes_to_registered_handler(self) -> None:
        """Verify that dispatch() invokes the correct handler with verb, target, and state."""
        registry = CommandRegistry()
        state = GameState(current_room_id="lobby")

        def handler(verb: str, target: str | None, game_state: GameState) -> str:
            self.assertEqual((verb, target, game_state), ("look", "mirror", state))
            return "ok"

        registry.register("look", handler)

        result = registry.dispatch(Command("look", "mirror"), state)

        self.assertEqual(result, "ok")

    def test_dispatch_returns_unknown_message_for_unregistered_verb(self) -> None:
        """Verify that dispatching an unregistered verb returns the default unknown-command message."""
        registry = CommandRegistry()
        state = GameState(current_room_id="lobby")

        result = registry.dispatch(Command("dance"), state)

        self.assertEqual(result, "I don't know how to 'dance'.")

    def test_known_verbs_are_sorted(self) -> None:
        """Verify that known_verbs() returns registered verbs in ascending alphabetical order."""
        registry = CommandRegistry()
        registry.register("quit", lambda *_: "")
        registry.register("look", lambda *_: "")
        registry.register("check", lambda *_: "")

        self.assertEqual(registry.known_verbs(), ["check", "look", "quit"])

    def test_register_target_state_handler_adapts_simple_handlers(self) -> None:
        """Verify that the shared helper adapts target/state handlers to registry handlers."""
        registry = CommandRegistry()
        state = GameState(current_room_id="lobby")
        seen: list[tuple[str | None, GameState]] = []

        def handler(target: str | None, game_state: GameState) -> str:
            seen.append((target, game_state))
            return "ok"

        register_target_state_handler(registry, handler, "look", "examine")

        result = registry.dispatch(Command("examine", "mirror"), state)

        self.assertEqual(result, "ok")
        self.assertEqual(seen, [("mirror", state)])


class GameStateTest(unittest.TestCase):
    """Verify core session bookkeeping."""

    def test_tick_reduces_time_and_tracks_moves(self) -> None:
        """Verify that tick() decrements time_remaining and increments move_count without ending the game."""
        state = GameState(
            current_room_id="lobby", time_remaining=45, seconds_per_action=15
        )

        state.tick()

        self.assertEqual(state.time_remaining, 30)
        self.assertEqual(state.move_count, 1)
        self.assertFalse(state.game_over)

    def test_tick_clamps_time_to_zero_and_ends_game(self) -> None:
        """Verify that tick() clamps time_remaining to zero and sets game_over when time runs out."""
        state = GameState(
            current_room_id="lobby", time_remaining=10, seconds_per_action=15
        )

        state.tick()

        self.assertEqual(state.time_remaining, 0)
        self.assertTrue(state.game_over)

    def test_flags_and_formatted_time_helpers(self) -> None:
        """Verify set_flag/has_flag round-trip and formatted_time M:SS output."""
        state = GameState(current_room_id="lobby", time_remaining=125)

        state.set_flag("step2_hands_washed")

        self.assertTrue(state.has_flag("step2_hands_washed"))
        self.assertFalse(state.has_flag("missing"))
        self.assertEqual(state.formatted_time(), "2:05")


class SharedDataLoaderTest(unittest.TestCase):
    """Verify shared YAML asset loading used across runtime modules."""

    def test_load_yaml_data_reads_repository_data_files(self) -> None:
        """Verify that load_yaml_data() successfully loads commands.yaml from the data directory."""
        raw = load_yaml_data("commands.yaml")

        self.assertIn("responses", raw)
        self.assertIn("unknown", raw["responses"])


class MainCompositionTest(unittest.TestCase):
    """Verify that the composition root selects and wires the expected engine type."""

    def test_main_builds_plain_engine_when_no_curses_is_requested(self) -> None:
        """Verify that `--no-curses` selects GameEngine and updates the engine ref cell."""
        rooms = {"lobby": object()}
        event_queue = object()
        registry = object()
        engine = Mock()

        with (
            patch(
                "argparse.ArgumentParser.parse_args",
                return_value=SimpleNamespace(no_curses=True),
            ),
            patch("main.build_world", return_value=rooms),
            patch("main.load_events", return_value=event_queue),
            patch("main.build_commands", return_value=registry) as build_commands_mock,
            patch("main.GameEngine", return_value=engine) as game_engine_mock,
        ):
            main_module.main()

        game_engine_mock.assert_called_once()
        built_rooms, state, built_registry, built_events = (
            game_engine_mock.call_args.args
        )
        self.assertIs(built_rooms, rooms)
        self.assertEqual(state.current_room_id, "lobby")
        self.assertIs(built_registry, registry)
        self.assertIs(built_events, event_queue)
        self.assertEqual(build_commands_mock.call_args.args[0], [engine])
        engine.run.assert_called_once_with()

    def test_main_builds_curses_engine_by_default(self) -> None:
        """Verify that the default startup path imports and runs CursesEngine."""
        rooms = {"lobby": object()}
        event_queue = object()
        registry = object()
        engine = Mock()

        with (
            patch(
                "argparse.ArgumentParser.parse_args",
                return_value=SimpleNamespace(no_curses=False),
            ),
            patch("main.build_world", return_value=rooms),
            patch("main.load_events", return_value=event_queue),
            patch("main.build_commands", return_value=registry) as build_commands_mock,
            patch(
                "game.curses_engine.CursesEngine", return_value=engine
            ) as curses_mock,
        ):
            main_module.main()

        curses_mock.assert_called_once()
        built_rooms, state, built_registry, built_events = curses_mock.call_args.args
        self.assertIs(built_rooms, rooms)
        self.assertEqual(state.current_room_id, "lobby")
        self.assertIs(built_registry, registry)
        self.assertIs(built_events, event_queue)
        self.assertEqual(build_commands_mock.call_args.args[0], [engine])
        engine.run.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
