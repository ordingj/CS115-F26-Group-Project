"""Entry point – Final Exam: Room 314."""

from __future__ import annotations

from game.command import CommandRegistry
from game.engine import GameEngine
from game.event import Event, EventQueue
from game.puzzle import (
    step1_is_correct,
    step1_roll,
    step2_mirror_text,
    step2_roll,
    step3_is_correct,
    step3_roll,
)
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

        # ── Step 3: janitor hallway puzzle ────────────────────────────────────
        elif room.room_id == "hallway_janitor" and verb in ("forward", "left", "right"):
            if not step3_is_correct(verb, state):
                # Wrong way — bounce through a flavour room. The flavour room's
                # forward exit is pointed back to hallway_janitor (set on entry),
                # so the player can try again without a re-roll.
                state.wrong_turns += 1
                state.current_room_id = destination_id
                engine.describe_current_room()
                return (
                    "\nThe hallway curves unexpectedly. After a few steps you "
                    "recognise the tiles — you've looped back. The janitor is "
                    "still mopping."
                )
            # Correct direction — advance past the janitor.
            state.puzzle_step = 3
            state.set_flag("step3_solved")

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
            # The wrong directions loop back through flavour rooms.
            for d in ("forward", "left", "right"):
                exit_node.exits[d] = "hallway_janitor" if d == mirror_dir else "flavour_copy_room"

        # Janitor hallway entry: roll Step 3 song clue on first visit;
        # wire exits and redirect the shared flavour room's forward exit back
        # here so wrong-way bounces return to the janitor (not the 4-way).
        elif destination_id == "hallway_janitor":
            if not state.has_flag("step3_rolled"):
                step3_roll(state)
                state.set_flag("step3_rolled")
            correct_dir = state.active_clues["step3_correct_dir"]
            janitor = engine.rooms["hallway_janitor"]
            for d in ("forward", "left", "right"):
                janitor.exits[d] = "hallway_final" if d == correct_dir else "flavour_copy_room"
            # Redirect wrong-way bounce destination back to janitor hallway.
            engine.rooms["flavour_copy_room"].exits["forward"] = "hallway_janitor"

        engine.describe_current_room()
        return ""

    for direction in ("forward", "back", "left", "right"):
        registry.register(direction, handle_move)

    # ── look / examine ─────────────────────────────────────────────────────────
    def handle_look(verb: str, target: str | None, state: GameState) -> str:
        engine = engine_ref[0]
        if engine is None:
            return ""
        # Targeted examine: specific items before falling back to full room description.
        if target == "mirror":
            room = engine.current_room()
            if room and room.room_id == "bathroom":
                if not state.has_flag("step2_hands_washed"):
                    return (
                        "The mirror is fogged from the motion-sensor sinks. You can "
                        "barely see your own reflection."
                    )
                return step2_mirror_text(state)
        if target == "sink":
            room = engine.current_room()
            if room and room.room_id == "bathroom":
                phase = room.attributes.get("wash_phase", 0)
                running = room.attributes.get("sink_running", False)
                if state.has_flag("step2_hands_washed"):
                    return "The sink is off. Your hands are already clean."
                if running:
                    hint = "rinse hands" if phase in (0, 2) else "stop"
                    return (
                        f"A motion-sensor sink. The water is running. "
                        f"(Try: {hint.upper()})"
                    )
                return (
                    "The sink is off. The motion sensor blinks. "
                    "(Try: STOP to pull your hands back)"
                )
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
        if room is None:
            return f"There is no '{target}' here to read."
        # Room-specific readable items.
        if room.room_id == "lobby" and target == "detour_sign":
            return "The sign reads: DETOUR → (an arrow points down the forward hallway)."
        if room.room_id == "bathroom" and target == "mirror":
            if not state.has_flag("step2_hands_washed"):
                return "The mirror is too fogged to read anything on it."
            return step2_mirror_text(state)
        if target in room.items:
            return f"You read the {room.items[target]}, but the text is hard to make out."
        return f"There is no '{target}' here to read."

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

    # ── rinse / wash ──────────────────────────────────────────────────────────
    # Handwashing puzzle — phase state lives in room.attributes["wash_phase"]:
    #   0  sink running, hands out        → 'rinse hands' to start
    #   1  sink off, hands soapy          → 'stop' to pull hands back
    #   2  sink running again, hands out  → 'rinse hands' quickly to finish
    #   3  hands clean, sink running      → 'stop' to finish
    #   4  done, sink off, hands clean
    def handle_rinse(verb: str, target: str | None, state: GameState) -> str:
        engine = engine_ref[0]
        room = engine.current_room() if engine else None
        if room is None or room.room_id != "bathroom":
            return "There's nothing to rinse here."
        if state.has_flag("step2_hands_washed"):
            return "Your hands are already clean."
        phase = room.attributes.get("wash_phase", 0)
        if phase == 0:
            # First attempt: water stops as soon as hands break the beam.
            room.attributes["wash_phase"] = 1
            room.attributes["sink_running"] = False
            return (
                "You hold your hands under the faucet. The water runs over them "
                "for a moment... then cuts off. Your hands are sudsy but the sensor "
                "timed out before you could rinse. Try 'stop' to let the sensor reset."
            )
        if phase == 2:
            # Trick: quick enough after 'stop' — water stays running this time.
            room.attributes["wash_phase"] = 3
            return (
                "You put your hands back under quickly. This time the water stays "
                "running long enough to rinse the soap off. Your hands are clean. "
                "Type 'stop' to take your hands away."
            )
        if phase == 1:
            return (
                "The water is off. Pull your hands back first — try 'stop' to let "
                "the motion sensor reset."
            )
        return "Your hands are already rinsed. Type 'stop' to finish."

    registry.register("rinse", handle_rinse)
    registry.register("wash", handle_rinse)

    # ── stop (take hands away from sink) ──────────────────────────────────────
    def handle_stop(verb: str, target: str | None, state: GameState) -> str:
        engine = engine_ref[0]
        room = engine.current_room() if engine else None
        if room is None or room.room_id != "bathroom":
            return "There's nothing to stop here."
        if state.has_flag("step2_hands_washed"):
            return "The sink is already off. Your hands are clean."
        phase = room.attributes.get("wash_phase", 0)
        if phase == 1:
            # Pull hands away after first rinse — sensor detects empty space,
            # water comes back on.
            room.attributes["wash_phase"] = 2
            room.attributes["sink_running"] = True
            return (
                "You pull your hands back. A moment passes... the sensor detects "
                "the empty basin and the water comes back on. Quick — rinse hands again."
            )
        if phase == 3:
            # Final stop after successful rinse — hands are clean.
            room.attributes["wash_phase"] = 4
            room.attributes["sink_running"] = False
            state.set_flag("step2_hands_washed")
            state.set_flag("step2_mirror_clue_visible")
            return (
                "You take your hands away. The water shuts off. Your hands are "
                "clean. The steam on the mirror has cleared a little. "
                "You should look at it."
            )
        if phase == 0:
            return "You step back from the sink. The water keeps running."
        return "You step back from the sink."

    registry.register("stop", handle_stop)

    # ── listen ──────────────────────────────────────────────────────
    def handle_listen(verb: str, target: str | None, state: GameState) -> str:
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
            return (
                "The janitor is humming. You catch a few bars of the chorus: "
                f"\n  \"{chorus}\""
            )
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
