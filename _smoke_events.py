"""Smoke test: ambient events fire correctly for location and move-count triggers."""
from game.event import EventQueue
from game.state import GameState
from main import build_events

# ── location-based ─────────────────────────────────────────────────────────────

def make_state(**kwargs):
    defaults = dict(current_room_id="lobby", move_count=0, wrong_turns=0, time_remaining=600)
    defaults.update(kwargs)
    s = GameState(current_room_id=defaults.pop("current_room_id"))
    for k, v in defaults.items():
        setattr(s, k, v)
    return s

def fired_ids(queue, state):
    msgs = queue.tick(state)
    return msgs

# Rebuild a fresh queue for each sub-test
def test_lobby_event():
    q = build_events()
    s = make_state(current_room_id="lobby", move_count=0)
    msgs = q.tick(s)  # move_count==0, should NOT fire lobby tile event
    assert not any("ceiling" in m for m in msgs), f"Fired too early: {msgs}"
    s.move_count = 1
    msgs = q.tick(s)
    assert any("ceiling" in m for m in msgs), f"Lobby tile event did not fire: {msgs}"
    print("lobby_ceiling_tiles: PASS")

def test_hallway_no_signal():
    q = build_events()
    s = make_state(current_room_id="hallway_approach")
    msgs = q.tick(s)
    assert any("signal" in m for m in msgs), f"No-signal event missing: {msgs}"
    msgs2 = q.tick(s)
    assert not any("signal" in m for m in msgs2), "Should be one-shot"
    print("hallway_no_signal: PASS")

def test_janitor_event():
    q = build_events()
    s = make_state(current_room_id="hallway_janitor")
    msgs = q.tick(s)
    assert any("mopping" in m for m in msgs), f"Janitor event missing: {msgs}"
    print("janitor_same_spot: PASS")

def test_move_count_events():
    q = build_events()
    s = make_state(current_room_id="lobby", move_count=3)
    msgs = q.tick(s)
    assert any("door closes" in m for m in msgs), f"door_closes missing: {msgs}"
    s.move_count = 8
    msgs = q.tick(s)
    assert any("footsteps" in m.lower() for m in msgs), f"footsteps missing: {msgs}"
    print("tension_door_closes + tension_footsteps_stop: PASS")

def test_time_3min():
    q = build_events()
    s = make_state(time_remaining=175)
    msgs = q.tick(s)
    assert any("three minutes" in m for m in msgs), f"3-min warning missing: {msgs}"
    print("time_warning_3min: PASS")

test_lobby_event()
test_hallway_no_signal()
test_janitor_event()
test_move_count_events()
test_time_3min()
print("ALL PASS")
