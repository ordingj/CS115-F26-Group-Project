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

from typing import Any, TypedDict, cast

from game import load_yaml_data
from game.room import Room


class _RequiredRoomEntry(TypedDict):
    """Required keys that every rooms.yaml entry must provide."""

    room_id: str
    name: str
    description: str


class _RoomEntry(_RequiredRoomEntry, total=False):
    """Typed representation of a single rooms.yaml entry.

    Inherits the required fields from :class:`_RequiredRoomEntry` and adds
    optional fields (``total=False`` means no field is required here).
    """

    exits: dict[str, str | None]
    items: dict[str, str]
    attributes: dict[str, Any]
    type: str


class _RoomsFile(TypedDict):
    """Typed representation of the rooms.yaml document root.

    The YAML file is expected to have a top-level ``rooms`` key containing
    a list of room entry mappings.
    """

    rooms: list[_RoomEntry]


# ── loader ─────────────────────────────────────────────────────────────────────


def _load_rooms() -> tuple[list[Room], list[str]]:
    """Parse ``data/rooms.yaml`` and return all rooms plus the flavor room IDs.

    Called once at module import time.  The results are cached in
    ``_ALL_ROOMS`` and ``FLAVOR_ROOM_POOL``; every subsequent
    :func:`build_world` call clones from those cached templates rather than
    re-parsing the YAML.

    Returns
    -------
    tuple[list[Room], list[str]]
        A 2-tuple of ``(all_room_objects, flavor_room_id_list)``.
    """
    raw = cast(_RoomsFile, load_yaml_data("rooms.yaml"))
    all_rooms: list[Room] = []
    flavor_ids: list[str] = []
    for entry in raw["rooms"]:
        # Default to "structural" for rooms that omit the optional type field.
        room_type = entry.get("type", "structural")
        room = Room(
            room_id=entry["room_id"],
            name=entry["name"],
            description=entry["description"],
            # Use empty dict as fallback when the field is absent or null.
            exits=entry.get("exits") or {},
            items=entry.get("items") or {},
            attributes=entry.get("attributes") or {},
        )
        all_rooms.append(room)
        # Collect flavor room IDs for the wrong-way detour pool used by
        # player_movement.py when a player picks the wrong direction.
        if room_type == "flavor":
            flavor_ids.append(room.room_id)
    return all_rooms, flavor_ids


_ALL_ROOMS, FLAVOR_ROOM_POOL = _load_rooms()

# ── public builder ─────────────────────────────────────────────────────────────


def build_world() -> dict[str, Room]:
    """Return the complete room dictionary keyed by ``room_id``.

    Each call clones the module-level room templates loaded from
    ``data/rooms.yaml`` at import time, so per-session mutations to exits or
    attributes (e.g. puzzle exit rewiring, bathroom wash-phase counters) do
    not leak into later calls to :func:`build_world` or other game sessions.

    Returns
    -------
    dict[str, Room]
        Mapping of ``room_id`` → fresh :class:`~game.room.Room` clone.
    """
    return {room.room_id: room.clone() for room in _ALL_ROOMS}
