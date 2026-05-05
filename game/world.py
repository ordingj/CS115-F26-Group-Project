"""World definition – all rooms for Final Exam: Room 314.

Rooms are split into two categories:

- **Structural rooms**: fixed nodes in the puzzle graph (lobby, intersections,
  bathroom, janitor hallway, Room 314).  Their exits that depend on puzzle state
  are set to ``None`` here; the puzzle logic in ``main.py`` will assign them at
  runtime.

- **Flavour rooms**: atmospheric filler inserted 1-3 at a time between puzzle
  nodes to add disorientation.  Their ``forward``/``back`` exits are wired
  dynamically by the routing logic; they are stored in ``FLAVOUR_ROOM_POOL``
  (list of room_ids) so routing code can reference them by name.
"""

from __future__ import annotations

from game.room import Room

# ── flavour room pool ──────────────────────────────────────────────────────────
# IDs of rooms that may be spliced into the path between puzzle nodes.
# forward/back exits are left empty here; routing logic sets them at runtime.

FLAVOUR_ROOM_POOL: list[str] = [
    "flavour_copy_room",
    "flavour_faculty_office",
    "flavour_study_lounge",
    "flavour_stairwell",
    "flavour_classroom_195",
    "flavour_water_fountain",
]


def _flavour_rooms() -> list[Room]:
    # All flavour rooms share the same exit structure: forward loops back to
    # intersection_4way (wrong-way bounce) and back is unset (routing logic may
    # chain several flavour rooms together via back as well).
    def _exits() -> dict[str, str | None]:
        return {"forward": "intersection_4way", "back": None}

    return [
        Room(
            room_id="flavour_copy_room",
            name="Copy Room",
            description=(
                "A copy room door is propped open with a ream of paper. The machine "
                "inside is running — printing page after page of what looks like exam "
                "questions. The output tray is already overflowing onto the floor. The "
                "pages are blank on the side facing up."
            ),
            exits=_exits(),
        ),
        Room(
            room_id="flavour_faculty_office",
            name="Faculty Office",
            description=(
                "A faculty office with the nameplate removed from the door. The door "
                "is slightly ajar. Through the gap you can see a desk covered in "
                "papers, a lamp still on, a chair pushed back as if someone just stood "
                "up. No one is visible. You hear nothing from inside."
            ),
            exits=_exits(),
        ),
        Room(
            room_id="flavour_study_lounge",
            name="Study Lounge",
            description=(
                "A small study lounge: two couches, a whiteboard, a table with a "
                "laptop open on it. The screen shows a campus map, but the building "
                "you're in isn't on it. The whiteboard reads GOOD LUCK in handwriting "
                "you almost recognise."
            ),
            exits=_exits(),
        ),
        Room(
            room_id="flavour_stairwell",
            name="Stairwell",
            description=(
                "A stairwell. The stairs go up but not down — there is a concrete "
                "wall where the lower flight should be. You are definitely on the "
                "ground floor. A flickering exit sign points in no particular "
                "direction."
            ),
            exits=_exits(),
        ),
        Room(
            room_id="flavour_classroom_195",
            name="Classroom 195",
            description=(
                "A classroom — the kind with fixed, bolted-down desks arranged in "
                "rows. The room number is 195. All the desks have been turned to face "
                "the back wall. A single sheet of paper sits on each desk, face-down."
            ),
            items={"paper": "a face-down sheet of paper"},
            exits=_exits(),
        ),
        Room(
            room_id="flavour_water_fountain",
            name="Hallway Nook",
            description=(
                "A hallway nook with a water fountain. You press the button. The water "
                "runs rust-brown for a few seconds, then clears. A handwritten note "
                "taped above it reads: PERFECTLY SAFE."
            ),
            exits=_exits(),
        ),
    ]


# ── structural rooms ───────────────────────────────────────────────────────────


def _structural_rooms() -> list[Room]:
    return [
        # ── lobby ──────────────────────────────────────────────────────────────
        Room(
            room_id="lobby",
            name="Building Lobby",
            description=(
                "The lobby is almost empty. Construction noise rumbles from the left "
                "hallway, blocked off with orange cones and caution tape. A "
                "hand-lettered detour sign points down a narrower hallway you've never "
                "noticed before. The fluorescent lights buzz at a frequency just below "
                "comfortable."
            ),
            # forward → approach hallway; left → construction (blocked)
            exits={"forward": "hallway_approach", "left": None},
            items={"detour_sign": "a hand-lettered detour sign"},
            attributes={"one_way": True},  # player cannot return once they leave
        ),
        # ── approach hallway (lobby → 4-way) ───────────────────────────────────
        Room(
            room_id="hallway_approach",
            name="Detour Hallway",
            description=(
                "A corridor you don't recognise, though you must have walked through "
                "it to get here. The room numbers don't match anything on the campus "
                "map: 207, 208, 502, 11. One door has a dry-erase board that reads "
                "FINAL EXAM TODAY in letters that are just slightly too large."
            ),
            # back is blocked — no returning to the lobby
            exits={"forward": "intersection_4way", "back": None},
        ),
        # ── 4-way intersection ─────────────────────────────────────────────────
        # forward/left/right exits are set dynamically by puzzle Step 1.
        # back leads to approach hallway (allows re-reading the clue, not a full reset).
        Room(
            room_id="intersection_4way",
            name="4-Way Intersection",
            description=(
                "A four-way intersection. Identical hallways stretch in every "
                "direction. The fluorescent light above flickers twice, then steadies. "
                "Something about this place feels like a reset."
            ),
            exits={"forward": None, "back": "hallway_approach", "left": None, "right": None},
            attributes={"is_puzzle_node": True, "puzzle_step": 1},
        ),
        # ── 3-way intersection (entering from 4-way side) ──────────────────────
        # forward → bathroom; left/right/back set by puzzle routing.
        Room(
            room_id="intersection_3way",
            name="3-Way Junction",
            description=(
                "The hallway opens into a three-way junction. A door labelled "
                "RESTROOMS faces you directly ahead. Two more hallways branch off to "
                "either side. The air smells faintly of bleach."
            ),
            exits={"forward": "bathroom", "left": None, "right": None, "back": None},
            attributes={"is_puzzle_node": True, "puzzle_step": 2},
        ),
        # ── bathroom ───────────────────────────────────────────────────────────
        # Puzzle Step 2 plays out here. Back exits to intersection_3way_exit.
        Room(
            room_id="bathroom",
            name="Restroom",
            description=(
                "The restroom is institutional and slightly too quiet. Three stall "
                "doors are visible — all locked. A row of sinks lines one wall, their "
                "motion-sensor faucets blinking on and off for no apparent reason. A "
                "mirror spans the full width of the wall above the sinks."
            ),
            exits={"back": "intersection_3way_exit"},
            items={"sink": "a motion-sensor sink", "mirror": "a large wall mirror"},
            attributes={
                "is_puzzle_node": True,
                "puzzle_step": 2,
                "sink_running": False,
                "hands_wet": False,
                "hands_soapy": False,
                "hands_rinsed": False,
                "stalls_locked": True,
                "mirror_clue_visible": False,
            },
        ),
        # ── 3-way intersection (exiting from bathroom) ─────────────────────────
        # Same physical location as intersection_3way but from the opposite
        # perspective: the bathroom door is now behind the player.
        # forward/left/right exits are set by puzzle routing (mirror clue direction).
        Room(
            room_id="intersection_3way_exit",
            name="3-Way Junction",
            description=(
                "The restroom door is now behind you. The same two hallways branch off "
                "to either side, and a third stretches ahead. The bleach smell "
                "lingers. You try to recall what the mirror said."
            ),
            exits={"back": "bathroom", "left": None, "right": None, "forward": None},
            attributes={"is_puzzle_node": True, "puzzle_step": 3},
        ),
        # ── janitor hallway ────────────────────────────────────────────────────
        Room(
            room_id="hallway_janitor",
            name="Janitor's Hallway",
            description=(
                "The hallway ahead shifts subtly — different tile pattern, or maybe "
                "the lighting changed. A janitor in grey coveralls is mopping the "
                "floor, earbuds in, humming something to himself. He hasn't noticed "
                "you, or doesn't care."
            ),
            exits={"back": "intersection_3way_exit", "left": None, "right": None, "forward": None},
            attributes={
                "is_puzzle_node": True,
                "puzzle_step": 4,
                "janitor_present": True,
                "song_heard": False,
            },
        ),
        # ── final hallway (janitor → Room 314) ─────────────────────────────────
        # forward/back exits set by routing; Room 314 is the destination.
        Room(
            room_id="hallway_final",
            name="Final Stretch",
            description=(
                "The room numbers are finally sequential: 308, 309, 310... You're "
                "close. The air feels different here — stiller, expectant."
            ),
            exits={"back": "hallway_janitor", "forward": "room_314"},
        ),
        # ── Room 314 ───────────────────────────────────────────────────────────
        Room(
            room_id="room_314",
            name="Room 314",
            description=(
                "Room 314. The door is unlocked. You push it open."
            ),
            exits={},
            attributes={"is_win_room": True},
        ),
    ]


# ── public builder ─────────────────────────────────────────────────────────────


def build_world() -> dict[str, Room]:
    """Return the complete room dictionary keyed by room_id."""
    rooms: dict[str, Room] = {}
    for room in _structural_rooms():
        rooms[room.room_id] = room
    for room in _flavour_rooms():
        rooms[room.room_id] = room
    return rooms
