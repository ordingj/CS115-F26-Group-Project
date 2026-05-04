"""GameState – single source of truth for all mutable game data."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GameState:
    """Holds all mutable state for a running game session.

    Attributes:
        current_room_id:    ID of the room the player is currently in.
        time_remaining:     Seconds left before game over (counts down).
        seconds_per_action: Clock cost of each player action.
        puzzle_step:        Current step in the main puzzle sequence (0 = not started).
        active_clues:       Randomised clue values for the current puzzle cycle.
        flags:              Arbitrary boolean flags (e.g. "washed_hands").
        move_count:         Total number of player actions taken.
        wrong_turns:        Number of times the player went the wrong way.
        game_over:          True when a terminal condition has been reached.
        won:                True if the player reached Room 314 in time.
    """

    # ── location ──────────────────────────────────────────────────────────────
    current_room_id: str

    # ── time ──────────────────────────────────────────────────────────────────
    time_remaining: int = 600           # 10 minutes in seconds
    seconds_per_action: int = 15        # cost per player command

    # ── puzzle progression ────────────────────────────────────────────────────
    puzzle_step: int = 0
    active_clues: dict[str, str] = field(default_factory=dict)

    # ── generic flags ─────────────────────────────────────────────────────────
    flags: dict[str, bool] = field(default_factory=dict)

    # ── session counters ──────────────────────────────────────────────────────
    move_count: int = 0
    wrong_turns: int = 0

    # ── terminal conditions ───────────────────────────────────────────────────
    game_over: bool = False
    won: bool = False

    # ── helpers ───────────────────────────────────────────────────────────────

    def tick(self) -> None:
        """Advance the clock by one action's worth of time."""
        self.time_remaining -= self.seconds_per_action
        self.move_count += 1
        if self.time_remaining <= 0:
            self.time_remaining = 0
            self.game_over = True

    def set_flag(self, key: str, value: bool = True) -> None:
        self.flags[key] = value

    def has_flag(self, key: str) -> bool:
        return self.flags.get(key, False)

    def formatted_time(self) -> str:
        """Return time as M:SS string."""
        minutes, seconds = divmod(max(self.time_remaining, 0), 60)
        return f"{minutes}:{seconds:02d}"
