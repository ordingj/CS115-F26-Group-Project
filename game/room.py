"""Room asset type for the text adventure."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Room:
    """A single location in the game world.

    Attributes:
        room_id:     Unique string identifier used as a dictionary key.
        name:        Short display name shown to the player (e.g. "Building Lobby").
        description: Full prose description printed when the player enters.
        exits:       Maps direction keyword -> destination room_id.
                     A value of None means the exit exists but is currently blocked.
        items:       Interactable objects in the room: {item_id: display_name}.
        attributes:  Arbitrary metadata for game logic (e.g. {"has_sink": True}).
    """

    room_id: str
    name: str
    description: str
    exits: dict[str, Optional[str]] = field(default_factory=dict)
    items: dict[str, str] = field(default_factory=dict)
    attributes: dict[str, object] = field(default_factory=dict)
