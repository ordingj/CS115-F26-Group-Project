"""Step 1 four-way intersection clue helpers.

This module owns the randomized clue generation, return-aware description,
clue formatting, and clue-specific read handlers used by the four-way
intersection puzzle node.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial
from typing import Any

from game.commands.command import RoomStateHandler, state_only_room_state_handler
from game import load_yaml_data
from game.puzzles.puzzle import active_clue_value, roll_active_clue
from game.room import Room
from game.state import GameState

_PUZZLE: dict = load_yaml_data("puzzle.yaml")

_STEP1_DIRS: list[str] = ["forward", "left", "right"]
_STEP1_CLUE_TEMPLATES: dict[str, str] = _PUZZLE["step1_clue_templates"]
_OPPOSITE: dict[str, str] = {
    "forward": "back",
    "back": "forward",
    "left": "right",
    "right": "left",
}
_STEP1_CLUE_TYPES: list[str] = list(_STEP1_CLUE_TEMPLATES)
_STEP1_FORWARD_CLUE_TYPES: tuple[str, ...] = tuple(
    clue_type for clue_type in _STEP1_CLUE_TYPES if clue_type != "shadow"
)
_STEP1_READABLE_TARGETS: dict[str, tuple[str, ...]] = {
    clue_type: tuple(targets)
    for clue_type, targets in _PUZZLE["step1_readable_targets"].items()
}


def step1_roll(state: GameState) -> None:
    """Randomly assign a correct direction and clue type for the 4-way puzzle."""
    correct_dir = roll_active_clue(state, "step1_correct_dir", _STEP1_DIRS)
    clue_types = (
        _STEP1_FORWARD_CLUE_TYPES if correct_dir == "forward" else _STEP1_CLUE_TYPES
    )
    roll_active_clue(state, "step1_clue_type", clue_types)


def step1_clue_text(state: GameState) -> str:
    """Return the formatted clue string for the current Step 1 roll."""
    correct_dir = active_clue_value(state, "step1_correct_dir")
    clue_type = active_clue_value(state, "step1_clue_type")
    template = _STEP1_CLUE_TEMPLATES.get(clue_type, "")
    if not (correct_dir and template):
        return ""
    opposite_dir = _OPPOSITE.get(correct_dir, "")
    return template.format(correct=correct_dir, opposite=opposite_dir)


def step1_read_text(state: GameState, target: str, not_here_template: str) -> str:
    """Return readable Step 1 clue text when the requested target is active."""
    clue_type = active_clue_value(state, "step1_clue_type")
    if target not in _STEP1_READABLE_TARGETS.get(clue_type, ()):
        return not_here_template.format(target=target)
    return step1_clue_text(state)


def intersection_read_target_handlers(
    commands: Mapping[str, Any],
) -> dict[tuple[str, str], RoomStateHandler]:
    """Return Step 1 room-target handlers for the ``read`` verb."""
    not_here_template = commands["read"]["not_here"]
    return {
        ("intersection_4way", target): state_only_room_state_handler(
            partial(step1_read_text, target=target, not_here_template=not_here_template)
        )
        for targets in _STEP1_READABLE_TARGETS.values()
        for target in targets
    }


def intersection_description(room: Room, state: GameState) -> str:
    """Return the Step 1 room description, adding the reset line only on return."""
    description = room.description
    if not state.has_flag("step1_returned_to_intersection"):
        return description
    return_text = str(room.attributes.get("return_text", ""))
    if not return_text:
        return description
    return f"{description} {return_text}"
