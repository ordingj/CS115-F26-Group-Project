"""World definition – all rooms for Final Exam: Room 314.

Room data lives in ``data/rooms.yaml`` (project root).  This module loads that
file at startup and converts each entry into a :class:`~game.room.Room` object.

Rooms are tagged with a ``type`` field in the YAML:

- ``structural`` – fixed puzzle-graph nodes (lobby, intersections, bathroom,
  janitor hallway, Room 314). Exits that depend on puzzle state are ``null``
  in the YAML and wired at runtime by ``main.py``.
- ``flavor``    – atmospheric filler inserted 1-3 at a time between puzzle
  nodes. Their ``forward``/``back`` exits are also wired at runtime; their
  IDs are exported via :data:`FLAVOR_ROOM_POOL`.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from game.room import Room

_DATA_FILE = Path(__file__).parent.parent / "data" / "rooms.yaml"

# ── loader ─────────────────────────────────────────────────────────────────────


def _load_rooms() -> tuple[list[Room], list[str]]:
    """Parse rooms.yaml and return (all_rooms, flavor_room_ids)."""
    raw: dict = yaml.safe_load(_DATA_FILE.read_text(encoding="utf-8"))
    all_rooms: list[Room] = []
    flavor_ids: list[str] = []
    for entry in raw["rooms"]:
        room_type = entry.pop("type", "structural")
        room = Room(
            room_id=entry["room_id"],
            name=entry["name"],
            description=entry["description"],
            exits=entry.get("exits") or {},
            items=entry.get("items") or {},
            attributes=entry.get("attributes") or {},
        )
        all_rooms.append(room)
        if room_type == "flavor":
            flavor_ids.append(room.room_id)
    return all_rooms, flavor_ids


_ALL_ROOMS, FLAVOR_ROOM_POOL = _load_rooms()

# ── public builder ─────────────────────────────────────────────────────────────


def build_world() -> dict[str, Room]:
    """Return the complete room dictionary keyed by room_id.

    Each call reloads from the module-level cache (``_ALL_ROOMS``), which was
    populated once at import time from ``data/rooms.yaml``.  Room attribute
    dicts are shared across calls, so callers that mutate attributes (e.g. the
    bathroom puzzle) will see their changes reflected on re-entry — which is the
    correct behaviour for a single game session.
    """
    return {room.room_id: room for room in _ALL_ROOMS}
