"""Entry point – Final Exam: Room 314."""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import yaml

from game.command import CommandRegistry
from game.engine import GameEngine
from game.event import EventQueue, load_events
from game.puzzle import (
    step1_is_correct,
    step1_roll,
    step2_mirror_text,
    step2_roll,
    step3_is_correct,
    step3_roll,
)
from game.state import GameState
from game.world import FLAVOR_ROOM_POOL, build_world

# ── static response strings (loaded from data/commands.yaml) ──────────────────
_CMD: dict = yaml.safe_load(
    (Path(__file__).parent / "data" / "commands.yaml").read_text(encoding="utf-8")
)["responses"]


# ── command builder ────────────────────────────────────────────────────────────


def build_commands(engine_ref: list[GameEngine | None]) -> CommandRegistry:
    """Register all player-facing commands and return the registry.

    ``engine_ref`` is a one-element list so handlers can reach the live engine
    without a circular import (the engine is not created until after the
    registry is built).

    Args:
        engine_ref: Mutable one-element list; ``engine_ref[0]`` will be the
                    live :class:`~game.engine.GameEngine` by the time any
                    handler is first called.

    Returns:
        A :class:`~game.command.CommandRegistry` with every verb registered.
    """
    registry = CommandRegistry()

    # ── movement ───────────────────────────────────────────────────────────────
    def handle_move(verb: str, target: str | None, state: GameState) -> str:
        """Move the player one step in *verb* direction.

        Validates the exit exists, applies puzzle-step routing logic for the
        4-way intersection (Step 1) and janitor hallway (Step 3), wires dynamic
        exits on key room transitions, and delegates room rendering to the engine.
        Sets ``state.won`` and ``state.game_over`` when Room 314 is reached.
        """
        engine = engine_ref[0]
        if engine is None:
            return "Error: engine not initialised."
        room = engine.current_room()
        if room is None:
            return "You are nowhere."
        if verb not in room.exits:
            return _CMD["move"]["no_exit"]
        destination_id = room.exits[verb]
        if destination_id is None:
            return _CMD["move"]["blocked"]

        # ── Step 1: 4-way intersection puzzle ─────────────────────────────────
        if room.room_id == "intersection_4way":
            if not step1_is_correct(verb, state):
                # Wrong way — bounce through a flavor room then back.
                state.wrong_turns += 1
                state.set_flag("step1_wrong_way", True)
                state.current_room_id = destination_id
                engine.describe_current_room()
                return _CMD["move"]["wrong_4way"]
            # Correct direction — advance puzzle state.
            state.puzzle_step = 1
            state.set_flag("step1_solved", True)

        # ── Step 3: janitor hallway puzzle ────────────────────────────────────
        elif room.room_id == "hallway_janitor" and verb in ("forward", "left", "right"):
            if not step3_is_correct(verb, state):
                # Wrong way — bounce through a flavor room. The flavor room's
                # forward exit is pointed back to hallway_janitor (set on entry),
                # so the player can try again without a re-roll.
                state.wrong_turns += 1
                state.current_room_id = destination_id
                engine.describe_current_room()
                return _CMD["move"]["wrong_janitor"]
            # Correct direction — advance past the janitor.
            state.puzzle_step = 3
            state.set_flag("step3_solved")

        state.current_room_id = destination_id

        # Roll a fresh Step 1 clue any time the player (re-)enters the 4-way.
        if destination_id == "intersection_4way":
            step1_roll(state)
            correct_dir = state.active_clues["step1_correct_dir"]
            intersection = engine.rooms["intersection_4way"]
            # Build a 2–3 room wrong-way chain from the flavor pool so lost
            # players traverse several atmospheric rooms before looping back.
            chain_len = random.randint(2, 3)
            chain = random.sample(FLAVOR_ROOM_POOL, chain_len)
            for i, room_id in enumerate(chain):
                next_id = chain[i + 1] if i + 1 < chain_len else "intersection_4way"
                engine.rooms[room_id].exits["forward"] = next_id
            # Correct direction → 3-way intersection; wrong → start of chain.
            for d in ("forward", "left", "right"):
                intersection.exits[d] = "intersection_3way" if d == correct_dir else chain[0]

        # Bathroom entry: roll Step 2 mirror direction, start sink running.
        elif destination_id == "bathroom":
            if not state.has_flag("step2_rolled"):
                step2_roll(state)
                state.set_flag("step2_rolled")
            bathroom = engine.rooms["bathroom"]
            bathroom.attributes["sink_running"] = True

        # Exiting bathroom back to 3-way (exit node): wire exits from mirror clue.
        elif destination_id == "intersection_3way_exit":
            mirror_dir = state.active_clues.get("step2_mirror_dir", "")
            exit_node = engine.rooms["intersection_3way_exit"]
            # The mirror clue direction leads toward the janitor hallway.
            # The wrong directions loop back through flavor rooms.
            for d in ("forward", "left", "right"):
                exit_node.exits[d] = "hallway_janitor" if d == mirror_dir else "flavor_copy_room"

        # Janitor hallway entry: roll Step 3 song clue on first visit;
        # wire exits and redirect the shared flavor room's forward exit back
        # here so wrong-way bounces return to the janitor (not the 4-way).
        elif destination_id == "hallway_janitor":
            if not state.has_flag("step3_rolled"):
                step3_roll(state)
                state.set_flag("step3_rolled")
            correct_dir = state.active_clues["step3_correct_dir"]
            janitor = engine.rooms["hallway_janitor"]
            for d in ("forward", "left", "right"):
                janitor.exits[d] = "hallway_final" if d == correct_dir else "flavor_copy_room"
            # Redirect wrong-way bounce destination back to janitor hallway.
            engine.rooms["flavor_copy_room"].exits["forward"] = "hallway_janitor"

        # Win condition: arriving at Room 314 ends the game as a win.
        elif destination_id == "room_314":
            state.won = True
            state.game_over = True

        engine.describe_current_room()
        return ""

    for direction in ("forward", "back", "left", "right"):
        registry.register(direction, handle_move)

    # ── look / examine ─────────────────────────────────────────────────────────
    def handle_look(verb: str, target: str | None, state: GameState) -> str:
        """Describe the current room, or examine a specific item.

        Special cases: ``look mirror`` and ``look sink`` in the bathroom show
        puzzle-relevant detail.  Any other target (or no target) triggers a
        full room redescription.
        """
        engine = engine_ref[0]
        if engine is None:
            return ""
        # Targeted examine: specific items before falling back to full room description.
        if target == "mirror":
            room = engine.current_room()
            if room and room.room_id == "bathroom":
                if not state.has_flag("step2_hands_washed"):
                    return _CMD["look"]["mirror_fogged"]
                return step2_mirror_text(state)
        if target == "sink":
            room = engine.current_room()
            if room and room.room_id == "bathroom":
                phase = room.attributes.get("wash_phase", 0)
                running = room.attributes.get("sink_running", False)
                if state.has_flag("step2_hands_washed"):
                    return _CMD["look"]["sink_clean"]
                if running:
                    key = "sink_running_rinse" if phase in (0, 2) else "sink_running_stop"
                    return _CMD["look"][key]
                return _CMD["look"]["sink_off"]
        engine.describe_current_room()
        return ""

    registry.register("look", handle_look)
    registry.register("examine", handle_look)

    # ── check watch ────────────────────────────────────────────────────────────
    def handle_check(verb: str, target: str | None, state: GameState) -> str:
        """Report the time remaining, or deflect if a non-watch target is given."""
        if target in (None, "watch", "time"):
            return _CMD["check"]["watch"].format(time=state.formatted_time())
        return _CMD["check"]["other"].format(target=target)

    registry.register("check", handle_check)

    # ── read ───────────────────────────────────────────────────────────────────
    def handle_read(verb: str, target: str | None, state: GameState) -> str:
        """Read a named item in the current room.

        Handles the lobby detour sign (accepts both ``"sign"`` and
        ``"detour_sign"``), the bathroom mirror (only readable after hands are
        washed), and any other item present in the room's item dict.
        """
        if target is None:
            return _CMD["read"]["no_target"]
        engine = engine_ref[0]
        room = engine.current_room() if engine else None
        if room is None:
            return _CMD["read"]["not_here"].format(target=target)
        # Room-specific readable items.
        if room.room_id == "lobby" and target in ("detour_sign", "sign"):
            return _CMD["read"]["detour_sign"]
        if room.room_id == "bathroom" and target == "mirror":
            if not state.has_flag("step2_hands_washed"):
                return _CMD["read"]["mirror_fogged"]
            return step2_mirror_text(state)
        if target in room.items:
            return _CMD["read"]["generic"].format(item=room.items[target])
        return _CMD["read"]["not_here"].format(target=target)

    registry.register("read", handle_read)

    # ── open ───────────────────────────────────────────────────────────────────
    def handle_open(verb: str, target: str | None, state: GameState) -> str:
        """Attempt to open a door or object (always blocked in this game)."""
        if target is None:
            return _CMD["open"]["no_target"]
        return _CMD["open"]["blocked"].format(target=target)

    registry.register("open", handle_open)

    # ── knock ──────────────────────────────────────────────────────────────────
    def handle_knock(verb: str, target: str | None, state: GameState) -> str:
        """Knock on a door or object (never answered)."""
        if target is None:
            return _CMD["knock"]["no_target"]
        return _CMD["knock"]["no_answer"].format(target=target)

    registry.register("knock", handle_knock)

    # ── rinse / wash ──────────────────────────────────────────────────────────
    # Handwashing puzzle — phase state lives in room.attributes["wash_phase"]:
    #   0  sink running, hands out        → 'rinse hands' to start
    #   1  sink off, hands soapy          → 'stop' to pull hands back
    #   2  sink running again, hands out  → 'rinse hands' quickly to finish
    #   3  hands clean, sink running      → 'stop' to finish
    #   4  done, sink off, hands clean
    def handle_rinse(verb: str, target: str | None, state: GameState) -> str:
        """Advance the handwashing puzzle one phase forward.

        Only active in the bathroom.  Interleaves with :func:`handle_stop`;
        the full sequence is: rinse → stop → rinse → stop.
        """
        engine = engine_ref[0]
        room = engine.current_room() if engine else None
        if room is None or room.room_id != "bathroom":
            return _CMD["rinse"]["no_location"]
        if state.has_flag("step2_hands_washed"):
            return _CMD["rinse"]["already_clean"]
        phase = room.attributes.get("wash_phase", 0)
        if phase == 0:
            # First attempt: water stops as soon as hands break the beam.
            room.attributes["wash_phase"] = 1
            room.attributes["sink_running"] = False
            return _CMD["rinse"]["phase_0"]
        if phase == 2:
            # Trick: quick enough after 'stop' — water stays running this time.
            room.attributes["wash_phase"] = 3
            return _CMD["rinse"]["phase_2"]
        if phase == 1:
            return _CMD["rinse"]["phase_1_wrong"]
        return _CMD["rinse"]["phase_done"]

    registry.register("rinse", handle_rinse)
    registry.register("wash", handle_rinse)

    # ── stop (take hands away from sink) ──────────────────────────────────────
    def handle_stop(verb: str, target: str | None, state: GameState) -> str:
        """Pull hands away from the sink, advancing the handwashing puzzle.

        On phase 1, the sensor detects the empty basin and restarts water.
        On phase 3, hands are marked clean and the mirror clue becomes readable.
        """
        engine = engine_ref[0]
        room = engine.current_room() if engine else None
        if room is None or room.room_id != "bathroom":
            return _CMD["stop"]["no_location"]
        if state.has_flag("step2_hands_washed"):
            return _CMD["stop"]["already_clean"]
        phase = room.attributes.get("wash_phase", 0)
        if phase == 1:
            # Pull hands away after first rinse — sensor detects empty space,
            # water comes back on.
            room.attributes["wash_phase"] = 2
            room.attributes["sink_running"] = True
            return _CMD["stop"]["phase_1"]
        if phase == 3:
            # Final stop after successful rinse — hands are clean.
            room.attributes["wash_phase"] = 4
            room.attributes["sink_running"] = False
            state.set_flag("step2_hands_washed")
            state.set_flag("step2_mirror_clue_visible")
            return _CMD["stop"]["phase_3"]
        if phase == 0:
            return _CMD["stop"]["phase_0"]
        return _CMD["stop"]["fallback"]

    registry.register("stop", handle_stop)

    # ── listen ──────────────────────────────────────────────────────
    def handle_listen(verb: str, target: str | None, state: GameState) -> str:
        """Listen to the janitor's humming to discover the Step 3 song clue.

        In the janitor hallway, prints the chorus line that encodes the correct
        exit direction.  Rolls the clue if the entry handler somehow didn't fire.
        """
        engine = engine_ref[0]
        room = engine.current_room() if engine else None
        if room and room.room_id == "hallway_janitor":
            chorus = state.active_clues.get("step3_song_chorus", "")
            if not chorus:
                # Fallback: roll now if entry handler somehow didn't fire.
                step3_roll(state)
                chorus = state.active_clues.get("step3_song_chorus", "")
            # Mark song as heard regardless of whether it was freshly rolled.
            room.attributes["song_heard"] = True
            state.set_flag("step3_song_heard")
            return _CMD["listen"]["janitor_prefix"] + f'\n  "{chorus}"'
        return _CMD["listen"]["silence"]

    registry.register("listen", handle_listen)

    # ── help ───────────────────────────────────────────────────────────────────
    def handle_help(verb: str, target: str | None, state: GameState) -> str:
        """List every registered command verb."""
        engine = engine_ref[0]
        verbs = engine.registry.known_verbs() if engine else []
        return "Commands: " + ", ".join(verbs)

    registry.register("help", handle_help)

    # ── quit ───────────────────────────────────────────────────────────────────
    def handle_quit(verb: str, target: str | None, state: GameState) -> str:
        """End the session gracefully; suppress the time-out losing screen."""
        state.quit = True
        state.game_over = True
        return _CMD["quit"]["farewell"]

    registry.register("quit", handle_quit)

    return registry


# ── event builder ──────────────────────────────────────────────────────────────


def build_events() -> EventQueue:
    """Load ambient and time-based narrative events from data/events.yaml."""
    return load_events()


# ── entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    """Parse CLI arguments, build the game world, and start the engine.

    Supports ``--no-curses`` to bypass the curses UI and run in plain stdout
    mode (useful for testing and TTYs that don't support curses).
    """
    ap = argparse.ArgumentParser(
        prog="main",
        description="Final Exam: Room 314 – a text adventure",
    )
    ap.add_argument(
        "--no-curses",
        action="store_true",
        help="Run in plain-text mode (no curses UI)",
    )
    args = ap.parse_args()

    rooms = build_world()
    state = GameState(current_room_id="lobby")
    event_queue = build_events()

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
