"""GameState – single source of truth for all mutable game data."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GameState:
    """Holds all mutable state for a running game session.

    A single ``GameState`` instance lives for the duration of one play-through
    and is shared between the engine, command handlers, and event system.  All
    fields are plain Python types so the whole object is trivially inspectable
    during testing.

    Attributes
    ----------
    current_room_id : str
        ID of the room the player is currently in.  Must match a key in the
        rooms dictionary returned by :func:`~game.world.build_world`.
    time_remaining : int
        Seconds left before the game ends in a loss.  Counts down by
        ``seconds_per_action`` after each player command.
    seconds_per_action : int
        Clock cost (in seconds) deducted from ``time_remaining`` per command.
    puzzle_step : int
        Current step in the main puzzle sequence.  ``0`` = not yet started;
        ``1`` = four-way solved; ``3`` = janitor puzzle solved.
    active_clues : dict[str, str]
        Randomised clue values for the current puzzle cycle, keyed by
        descriptive names such as ``"step1_correct_dir"``.
    flags : dict[str, bool]
        Arbitrary boolean flags checked by commands and events
        (e.g. ``"step2_hands_washed"``).
    inventory : list[str]
        Item names the player is currently carrying.
    move_count : int
        Total number of player commands executed this session.
    wrong_turns : int
        Number of times the player chose the wrong puzzle direction.
    game_over : bool
        ``True`` once any terminal condition (timeout, win, quit) is reached.
    won : bool
        ``True`` if the player successfully reached Room 314 in time.
    quit : bool
        ``True`` if the player voluntarily quit via the quit command.
    """

    # ── location ──────────────────────────────────────────────────────────────
    current_room_id: str

    # ── time ──────────────────────────────────────────────────────────────────
    time_remaining: int = 600  # 10 minutes in seconds
    seconds_per_action: int = 15  # cost per player command

    # ── puzzle progression ────────────────────────────────────────────────────
    puzzle_step: int = 0
    active_clues: dict[str, str] = field(default_factory=dict)

    # ── generic flags ─────────────────────────────────────────────────────────
    flags: dict[str, bool] = field(default_factory=dict)

    # ── inventory ─────────────────────────────────────────────────────────────
    inventory: list[str] = field(
        default_factory=lambda: ["watch", "backpack", "phone", "keys", "wallet"]
    )

    # ── session counters ──────────────────────────────────────────────────────
    move_count: int = 0
    wrong_turns: int = 0

    # ── terminal conditions ───────────────────────────────────────────────────
    game_over: bool = False
    won: bool = False
    quit: bool = False

    # ── helpers ───────────────────────────────────────────────────────────────

    def tick(self) -> None:
        """Advance the clock by one action's worth of time.

        Subtracts ``seconds_per_action`` from ``time_remaining`` and
        increments ``move_count``.  When time hits zero the clock is clamped
        and ``game_over`` is set so the engine exits its main loop.
        """
        self.time_remaining -= self.seconds_per_action
        self.move_count += 1
        if self.time_remaining <= 0:
            self.time_remaining = 0
            self.game_over = True

    def set_flag(self, key: str, value: bool = True) -> None:
        """Set an arbitrary boolean flag by name.

        Parameters
        ----------
        key : str
            Flag name (e.g. ``"step2_hands_washed"``).
        value : bool, optional
            Value to store; defaults to ``True``.
        """
        self.flags[key] = value

    def has_flag(self, key: str) -> bool:
        """Return the flag's value, or ``False`` if it has never been set.

        Parameters
        ----------
        key : str
            Flag name to look up.

        Returns
        -------
        bool
            The stored value, or ``False`` when the key is absent.
        """
        return self.flags.get(key, False)

    def formatted_time(self) -> str:
        """Return the time remaining as a human-readable ``M:SS`` string.

        Returns
        -------
        str
            Time remaining formatted as ``"M:SS"`` (e.g. ``"9:45"``).  The
            value is clamped to ``0:00`` so it never goes negative.
        """
        minutes, seconds = divmod(max(self.time_remaining, 0), 60)
        return f"{minutes}:{seconds:02d}"
