"""Unit tests for command, state, and shared data helpers.

Covers :class:`~game.command.CommandParser`, :class:`~game.command.CommandRegistry`,
:class:`~game.state.GameState`, and :func:`~game.load_yaml_data`.
"""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import game.main as main_module
from game import load_yaml_data
from game.commands.command import (
    Command,
    CommandParser,
    CommandRegistry,
    fixed_room_state_handler,
    register_target_state_command_specs,
    register_room_state_command_specs,
    register_room_state_handler,
    register_room_target_command_specs,
    register_room_target_state_handler,
    register_target_state_handler,
    TargetStateCommandSpec,
    RoomStateCommandSpec,
    RoomTargetCommandSpec,
    state_only_room_state_handler,
)
from game.room import Room
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
            """Assert that dispatch forwards the parsed command fields unchanged."""
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
            """Capture the adapted target/state pair for the assertion below."""
            seen.append((target, game_state))
            return "ok"

        register_target_state_handler(registry, handler, "look", "examine")

        result = registry.dispatch(Command("examine", "mirror"), state)

        self.assertEqual(result, "ok")
        self.assertEqual(seen, [("mirror", state)])

    def test_register_room_state_handler_gates_on_current_room(self) -> None:
        """Verify that room-gated handlers run only in the matching room."""
        registry = CommandRegistry()
        state = GameState(current_room_id="bathroom")
        bathroom = Room("bathroom", "Bathroom", "", attributes={"sink": True})
        current_room = Mock(return_value=bathroom)

        def handler(room: Room, game_state: GameState) -> str:
            """Assert that the room-gated adapter forwards the active room and state."""
            self.assertIs(room, bathroom)
            self.assertIs(game_state, state)
            return "washed"

        register_room_state_handler(
            registry,
            current_room,
            "bathroom",
            "not here",
            handler,
            "wash",
        )

        result = registry.dispatch(Command("wash"), state)

        self.assertEqual(result, "washed")

        current_room.return_value = Room("lobby", "Lobby", "")

        missing = registry.dispatch(Command("wash"), state)

        self.assertEqual(missing, "not here")

    def test_fixed_room_state_handler_returns_static_response(self) -> None:
        """Verify that the shared fixed room/state adapter ignores room and state."""
        state = GameState(current_room_id="bathroom")
        bathroom = Room("bathroom", "Bathroom", "")

        handler = fixed_room_state_handler("static")

        self.assertEqual(handler(bathroom, state), "static")

    def test_state_only_room_state_handler_delegates_to_state_only_handler(
        self,
    ) -> None:
        """Verify that the shared adapter forwards only the game state to the wrapped handler."""
        state = GameState(current_room_id="bathroom")
        bathroom = Room("bathroom", "Bathroom", "")
        seen: list[GameState] = []

        def handler(game_state: GameState) -> str:
            """Capture the forwarded state for the assertion below."""
            seen.append(game_state)
            return "mirror"

        adapted = state_only_room_state_handler(handler)

        self.assertEqual(adapted(bathroom, state), "mirror")
        self.assertEqual(seen, [state])

    def test_register_room_target_state_handler_prefers_room_target_match(self) -> None:
        """Verify that room-target handlers win before the generic fallback."""
        registry = CommandRegistry()
        state = GameState(current_room_id="bathroom")
        bathroom = Room("bathroom", "Bathroom", "")
        current_room = Mock(return_value=bathroom)
        fallback = Mock(return_value="fallback")

        def handler(room: Room, game_state: GameState) -> str:
            """Assert that the room-target adapter passes through the matched room and state."""
            self.assertIs(room, bathroom)
            self.assertIs(game_state, state)
            return "mirror"

        register_room_target_state_handler(
            registry,
            current_room,
            {("bathroom", "mirror"): handler},
            fallback,
            "look",
        )

        result = registry.dispatch(Command("look", "mirror"), state)

        self.assertEqual(result, "mirror")
        fallback.assert_not_called()

        current_room.return_value = Room("lobby", "Lobby", "")

        missing = registry.dispatch(Command("look", "mirror"), state)

        self.assertEqual(missing, "fallback")
        fallback.assert_called_once_with("mirror", state)

    def test_register_room_state_command_specs_registers_each_spec(self) -> None:
        """Verify that the shared batch helper wires each room-gated spec under all its verbs."""
        registry = CommandRegistry()
        state = GameState(current_room_id="bathroom")
        bathroom = Room("bathroom", "Bathroom", "")
        current_room = Mock(return_value=bathroom)
        seen: list[tuple[Room, GameState]] = []

        def handler(room: Room, game_state: GameState) -> str:
            """Capture the room/state pair registered under each room-gated verb."""
            seen.append((room, game_state))
            return "washed"

        command_specs: tuple[RoomStateCommandSpec, ...] = (
            (("wash", "rinse"), "bathroom", "not here", handler),
        )

        register_room_state_command_specs(registry, current_room, command_specs)

        self.assertEqual(registry.dispatch(Command("rinse"), state), "washed")
        self.assertEqual(seen, [(bathroom, state)])

    def test_register_room_target_command_specs_registers_each_spec(self) -> None:
        """Verify that the shared batch helper wires room-target specs and preserves fallback behavior."""
        registry = CommandRegistry()
        state = GameState(current_room_id="bathroom")
        bathroom = Room("bathroom", "Bathroom", "")
        current_room = Mock(return_value=bathroom)
        fallback = Mock(return_value="fallback")

        def handler(room: Room, game_state: GameState) -> str:
            """Assert that the matching room-target handler receives the live room and state."""
            self.assertIs(room, bathroom)
            self.assertIs(game_state, state)
            return "mirror"

        command_specs: tuple[RoomTargetCommandSpec, ...] = (
            (("look",), {("bathroom", "mirror"): handler}, fallback),
        )

        register_room_target_command_specs(registry, current_room, command_specs)

        self.assertEqual(registry.dispatch(Command("look", "mirror"), state), "mirror")

        current_room.return_value = Room("lobby", "Lobby", "")

        self.assertEqual(
            registry.dispatch(Command("look", "mirror"), state), "fallback"
        )
        fallback.assert_called_once_with("mirror", state)

    def test_register_target_state_command_specs_registers_each_spec(self) -> None:
        """Verify that the shared batch helper wires each simple handler under all its verbs."""
        registry = CommandRegistry()
        state = GameState(current_room_id="lobby")
        seen: list[tuple[str | None, GameState]] = []

        def handler(target: str | None, game_state: GameState) -> str:
            """Capture the adapted target/state values for each registered verb."""
            seen.append((target, game_state))
            return "ok"

        command_specs: tuple[TargetStateCommandSpec, ...] = (
            (("look", "examine"), handler),
        )

        register_target_state_command_specs(registry, command_specs)

        self.assertEqual(registry.dispatch(Command("examine", "mirror"), state), "ok")
        self.assertEqual(seen, [("mirror", state)])


class GameStateTest(unittest.TestCase):
    """Verify core session bookkeeping."""

    def test_start_countdown_syncs_remaining_from_live_deadline(self) -> None:
        """Verify that sync_time updates the countdown from a live deadline."""
        state = GameState(current_room_id="lobby", time_remaining=45)

        state.start_countdown(now=100.0)
        changed = state.sync_time(now=110.1)

        self.assertTrue(changed)
        self.assertEqual(state.time_remaining, 35)
        self.assertFalse(state.game_over)

    def test_tick_shifts_live_deadline_by_action_cost(self) -> None:
        """Verify that tick() still applies the action penalty in live mode."""
        state = GameState(
            current_room_id="lobby", time_remaining=45, seconds_per_action=15
        )

        state.start_countdown(now=100.0)
        state.tick(now=100.0)

        self.assertEqual(state.time_remaining, 30)
        self.assertEqual(state.move_count, 1)
        self.assertFalse(state.game_over)

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

    def test_tick_stops_advancing_after_winning(self) -> None:
        """Verify that post-win commands do not drain time or moves before exit."""
        state = GameState(
            current_room_id="room_314", time_remaining=45, seconds_per_action=15
        )
        state.won = True

        state.tick()

        self.assertEqual(state.time_remaining, 45)
        self.assertEqual(state.move_count, 0)
        self.assertFalse(state.game_over)

    def test_used_interstitial_room_ids_default_to_an_isolated_empty_set(self) -> None:
        """Verify that each GameState gets its own interstitial-room history set."""
        first_state = GameState(current_room_id="lobby")
        second_state = GameState(current_room_id="lobby")

        first_state.used_interstitial_room_ids.add("flavor_copy_room")

        self.assertEqual(second_state.used_interstitial_room_ids, set())

    def test_replay_requested_defaults_to_false(self) -> None:
        """Verify that fresh game state does not request a replay by default."""
        state = GameState(current_room_id="lobby")

        self.assertFalse(state.replay_requested)

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
        engine.state.replay_requested = False

        with (
            patch(
                "argparse.ArgumentParser.parse_args",
                return_value=SimpleNamespace(no_curses=True),
            ),
            patch.object(main_module, "build_world", return_value=rooms),
            patch.object(main_module, "load_events", return_value=event_queue),
            patch.object(
                main_module, "build_commands", return_value=registry
            ) as build_commands_mock,
            patch.object(
                main_module, "GameEngine", return_value=engine
            ) as game_engine_mock,
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
        engine.state.replay_requested = False

        with (
            patch(
                "argparse.ArgumentParser.parse_args",
                return_value=SimpleNamespace(no_curses=False),
            ),
            patch.object(main_module, "build_world", return_value=rooms),
            patch.object(main_module, "load_events", return_value=event_queue),
            patch.object(
                main_module, "build_commands", return_value=registry
            ) as build_commands_mock,
            patch(
                "game.engine.curses_engine.CursesEngine", return_value=engine
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

    def test_main_rebuilds_plain_engine_when_replay_is_requested(self) -> None:
        """Verify that main() starts a fresh session when the ending screen requests replay."""
        rooms = [{"lobby": object()}, {"lobby": object()}]
        events = [object(), object()]
        registries = [object(), object()]
        first_engine = Mock()
        first_engine.state.replay_requested = True
        second_engine = Mock()
        second_engine.state.replay_requested = False

        with (
            patch(
                "argparse.ArgumentParser.parse_args",
                return_value=SimpleNamespace(no_curses=True),
            ),
            patch.object(main_module, "build_world", side_effect=rooms),
            patch.object(main_module, "load_events", side_effect=events),
            patch.object(
                main_module, "build_commands", side_effect=registries
            ) as build_commands_mock,
            patch.object(
                main_module,
                "GameEngine",
                side_effect=[first_engine, second_engine],
            ) as game_engine_mock,
        ):
            main_module.main()

        self.assertEqual(game_engine_mock.call_count, 2)
        self.assertEqual(build_commands_mock.call_count, 2)
        first_engine.run.assert_called_once_with()
        second_engine.run.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
