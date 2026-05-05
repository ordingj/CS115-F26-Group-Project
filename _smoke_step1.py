"""Smoke test: wrong-way chain at intersection_4way."""
import random

random.seed(42)

from game.command import CommandParser
from game.engine import GameEngine
from game.puzzle import step1_roll
from game.state import GameState
from game.world import FLAVOUR_ROOM_POOL, build_world
from main import build_commands, build_events

rooms = build_world()
state = GameState(current_room_id="intersection_4way")
engine_ref: list = [None]
registry = build_commands(engine_ref)
engine = GameEngine(rooms, state, registry, build_events())
engine_ref[0] = engine

step1_roll(state)
correct = state.active_clues["step1_correct_dir"]
chain_len = random.randint(2, 3)
chain = random.sample(FLAVOUR_ROOM_POOL, chain_len)
for i, rid in enumerate(chain):
    nxt = chain[i + 1] if i + 1 < chain_len else "intersection_4way"
    engine.rooms[rid].exits["forward"] = nxt
for d in ("forward", "left", "right"):
    engine.rooms["intersection_4way"].exits[d] = (
        "intersection_3way" if d == correct else chain[0]
    )

print(f"correct={correct}  chain({chain_len})={chain}")
wrong = next(d for d in ("forward", "left", "right") if d != correct)
p = CommandParser()
registry.dispatch(p.parse(wrong), state)
print(f"after wrong move: {state.current_room_id}")
for step_n in range(chain_len):
    registry.dispatch(p.parse("forward"), state)
    print(f"  forward[{step_n + 1}] -> {state.current_room_id}")

assert state.current_room_id == "intersection_4way", f"Expected back at 4way, got {state.current_room_id}"
assert state.active_clues.get("step1_correct_dir"), "clue should be re-rolled"
print("PASS")
