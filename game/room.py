"""Room asset type for the text adventure."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field


@dataclass
class Room:
    """A single location in the game world.

    Rooms are loaded from ``data/rooms.yaml`` and then cloned by
    :func:`~game.world.build_world` on each new game session so per-session
    mutations (e.g. exit rewiring, puzzle attribute changes) never contaminate
    the module-level template.

    Attributes
    ----------
    room_id : str
        Unique string identifier used as the dictionary key in the world map
        (e.g. ``"bathroom"``, ``"intersection_4way"``).
    name : str
        Short display name shown to the player (e.g. ``"Building Lobby"``).
    description : str
        Full prose description printed when the player enters the room.
    exits : dict[str, str | None]
        Maps a direction keyword (``"forward"``, ``"back"``, ``"left"``,
        ``"right"``) to a destination ``room_id``.  A ``None`` value means
        the exit exists narratively but is currently blocked.
    items : dict[str, str]
        Interactable objects in the room, keyed by item ID with the display
        name as the value (e.g. ``{"sign": "DETOUR sign"}``).
    attributes : dict[str, object]
        Arbitrary metadata used by game logic (e.g.
        ``{"has_sink": True, "wash_phase": 0}``).
    """

    room_id: str
    name: str
    description: str
    exits: dict[str, str | None] = field(default_factory=dict)
    items: dict[str, str] = field(default_factory=dict)
    attributes: dict[str, object] = field(default_factory=dict)

    def clone(self) -> "Room":
        """Return a deep-copied instance of this room for a fresh world build.

        :meth:`deepcopy` is used for ``exits``, ``items``, and ``attributes``
        so that mutating one session's room data (e.g. rewiring exits during
        a puzzle step) does not affect other sessions or the module-level
        template stored in ``game/world.py``.

        Returns
        -------
        Room
            A new :class:`Room` with identical data but fully independent
            mutable containers.
        """
        return Room(
            room_id=self.room_id,
            name=self.name,
            description=self.description,
            exits=deepcopy(self.exits),
            items=deepcopy(self.items),
            attributes=deepcopy(self.attributes),
        )
