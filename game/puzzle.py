"""Puzzle logic for Final Exam: Room 314.

Each puzzle step is self-contained here so the modules that use it (engine,
main) stay readable.  All randomised results are stored in ``GameState`` so
the event system and command handlers can read them without re-rolling.

Active-clue keys used by each step
───────────────────────────────────
Step 1 (4-way intersection):
    ``step1_correct_dir``   – "forward" | "left" | "right"
    ``step1_clue_type``     – "light" | "sign" | "shadow"

Step 2 (bathroom mirror):
    ``step2_mirror_dir``    – "left" | "right"

Step 3/4 (janitor song):
    ``step3_song_title``    – song title string
    ``step3_song_chorus``   – lyric line containing the direction word
    ``step3_correct_dir``   – "left" | "right"
"""

from __future__ import annotations

import random

from game.state import GameState

# ── Step 1 – 4-way intersection ───────────────────────────────────────────────

_STEP1_DIRS: list[str] = ["forward", "left", "right"]

# Maps (clue_type, correct_dir) → clue text template.
# {correct} will be replaced with the actual direction shown/implied.
_STEP1_CLUE_TEMPLATES: dict[str, str] = {
    # Flickering light: player should go the OPPOSITE direction to the flicker.
    "light": (
        "The fluorescent light above the {opposite} hallway flickers and buzzes, "
        "throwing that corridor into a strobing half-dark. Every other direction "
        "is steady."
    ),
    # Bake-sale sign: arrow points the correct way.
    "sign": (
        "A bright orange flyer is taped to the wall: "
        "\"CS CLUB BAKE SALE – THIS WAY →\" "
        "with a hand-drawn arrow pointing {correct}."
    ),
    # Shadow: disappears around the corner in the correct direction.
    "shadow": (
        "Out of the corner of your eye you catch a shadow — someone, or something — "
        "slipping around the corner to your {correct}. "
        "By the time you look directly, it's gone."
    ),
}

_OPPOSITE: dict[str, str] = {
    "forward": "back",
    "back": "forward",
    "left": "right",
    "right": "left",
}


def step1_roll(state: GameState) -> None:
    """Randomly assign a new correct direction and clue type for the 4-way
    intersection.  Results are stored in ``state.active_clues``; call this
    every time the player enters (or re-enters) the intersection.
    """
    correct_dir = random.choice(_STEP1_DIRS)
    clue_type = random.choice(list(_STEP1_CLUE_TEMPLATES.keys()))
    state.active_clues["step1_correct_dir"] = correct_dir
    state.active_clues["step1_clue_type"] = clue_type


def step1_clue_text(state: GameState) -> str:
    """Return the formatted clue string for the current Step 1 roll.

    Returns an empty string if no roll has been performed yet.
    """
    correct_dir = state.active_clues.get("step1_correct_dir", "")
    clue_type = state.active_clues.get("step1_clue_type", "")
    template = _STEP1_CLUE_TEMPLATES.get(clue_type, "")
    if not (correct_dir and template):
        return ""
    opposite_dir = _OPPOSITE.get(correct_dir, "")
    return template.format(correct=correct_dir, opposite=opposite_dir)


def step1_is_correct(direction: str, state: GameState) -> bool:
    """Return True if *direction* matches the current Step 1 correct direction."""
    return direction == state.active_clues.get("step1_correct_dir", "")


# ── Step 2 – bathroom mirror ───────────────────────────────────────────────────


def step2_roll(state: GameState) -> None:
    """Randomly assign left or right as the bathroom mirror clue direction."""
    state.active_clues["step2_mirror_dir"] = random.choice(["left", "right"])


def step2_mirror_text(state: GameState) -> str:
    """Return what the mirror shows (only readable after hands are washed)."""
    direction = state.active_clues.get("step2_mirror_dir", "")
    if not direction:
        return ""
    # Backwards text effect: the mirror shows "TFEL OG" or "THGIR OG"
    backwards = ("GO " + direction.upper())[::-1]
    return (
        f'The mirror is fogged from the sinks. You wipe a clear patch. '
        f'Above the door frame, written in what looks like dry-erase marker, '
        f'you can barely make out: "{backwards}" — backwards, of course. It says: GO {direction.upper()}.'
    )


# ── Step 3/4 – janitor song ────────────────────────────────────────────────────

# 10 songs hinting LEFT, 10 hinting RIGHT.
# Each entry: (title, chorus_line)  – chorus contains the direction word.
_LEFT_SONGS: list[tuple[str, str]] = [
    ("One Step Left",          "One step left, then you're home."),
    ("Turn to the Left",       "Turn to the left, don't look back."),
    ("Left Side of the Road",  "Always on the left side of the road."),
    ("Left Behind",            "You left me left behind."),
    ("Take a Left",            "Take a left at the end of the hall."),
    ("Left of Center",         "I live just to the left of center."),
    ("Keep Left",              "Keep left, keep left, keep left 'til the end."),
    ("The Left Hand Path",     "Walk the left hand path with me."),
    ("Left Turn Only",         "Left turn only, no going back."),
    ("Left in the Dark",       "Left in the dark, and I can't find the light."),
]

_RIGHT_SONGS: list[tuple[str, str]] = [
    ("Turn Right",             "Turn right when the hallway forks."),
    ("Right Here Waiting",     "Right here waiting, right here for you."),
    ("Right Side of History",  "Standing on the right side of history."),
    ("Dead Right",             "Dead right, dead right, you know I'm right."),
    ("Two Rights",             "Two rights make a wrong, but one right gets you home."),
    ("Right Around the Corner","It's right around the corner, just stay on course."),
    ("Always Right",           "Always right, even when I'm wrong."),
    ("Hard Right",             "Hard right, hard right, commit to the turn."),
    ("Right Place Wrong Time", "Right place, wrong time, story of my life."),
    ("Right as Rain",          "Right as rain and twice as cold."),
]


def step3_roll(state: GameState) -> None:
    """Randomly select a song (and implied direction) for the janitor encounter."""
    direction = random.choice(["left", "right"])
    pool = _LEFT_SONGS if direction == "left" else _RIGHT_SONGS
    title, chorus = random.choice(pool)
    state.active_clues["step3_correct_dir"] = direction
    state.active_clues["step3_song_title"] = title
    state.active_clues["step3_song_chorus"] = chorus


def step3_chorus_text(state: GameState) -> str:
    """Return the chorus line the janitor is humming."""
    return state.active_clues.get("step3_song_chorus", "")


def step3_is_correct(direction: str, state: GameState) -> bool:
    """Return True if *direction* matches the current Step 3 correct direction."""
    return direction == state.active_clues.get("step3_correct_dir", "")
