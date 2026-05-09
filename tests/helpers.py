"""Shared test builders for Final Exam: Room 314.

Provides factory helpers that wire up a full :class:`~game.engine.GameEngine`
(or :class:`~game.curses_engine.CursesEngine`) with world, state, and command
registry in one call, reducing boilerplate across test modules.
"""

from __future__ import annotations

from typing import TypeVar, cast
from unittest.mock import Mock

from game.command import Command
from game.curses_engine import CursesEngine
from game.engine import GameEngine
from game.event import EventQueue
from game.player_commands import build_commands
from game.state import GameState
from game.world import build_world

EngineT = TypeVar("EngineT", bound=GameEngine)
"""Generic type variable for :class:`~game.engine.GameEngine` subclasses."""


def _build_engine(
    engine_type: type[EngineT], *, start_room: str = "lobby", time_remaining: int = 600
) -> EngineT:
    """Construct one engine with world, state, and commands fully wired.

    Parameters
    ----------
    engine_type : type[EngineT]
        :class:`~game.engine.GameEngine` or a subclass such as
        :class:`~game.curses_engine.CursesEngine`.
    start_room : str, optional
        ``room_id`` to start the player in.
    time_remaining : int, optional
        Starting countdown in seconds.

    Returns
    -------
    EngineT
        A fully initialised engine instance.
    """
    rooms = build_world()
    state = GameState(current_room_id=start_room, time_remaining=time_remaining)
    engine_ref: list[GameEngine | None] = [None]
    registry = build_commands(engine_ref)
    engine = engine_type(rooms, state, registry, EventQueue())
    engine_ref[0] = engine
    return engine


def make_engine(
    start_room: str = "lobby", *, time_remaining: int = 600, mock_describe: bool = True
) -> GameEngine:
    """Build a plain :class:`~game.engine.GameEngine` for tests.

    Parameters
    ----------
    start_room : str, optional
        ``room_id`` to start the player in.
    time_remaining : int, optional
        Starting countdown in seconds.
    mock_describe : bool, optional
        When ``True`` (default), ``engine.describe_current_room`` is replaced
        with a :class:`~unittest.mock.Mock` so tests that only care about
        command responses and state changes don't trigger room rendering.
        Pass ``False`` when the test needs real textual output.

    Returns
    -------
    GameEngine
        Fully wired engine with ``describe_current_room`` optionally mocked.
    """
    engine = _build_engine(
        GameEngine,
        start_room=start_room,
        time_remaining=time_remaining,
    )
    if mock_describe:
        engine.describe_current_room = Mock()  # type: ignore[method-assign]
    return engine


def make_curses_engine(start_room: str = "lobby") -> CursesEngine:
    """Build a :class:`~game.curses_engine.CursesEngine` without starting curses.

    Parameters
    ----------
    start_room : str, optional
        ``room_id`` to start the player in.

    Returns
    -------
    CursesEngine
        Fully wired curses engine (curses loop not started).
    """
    return _build_engine(CursesEngine, start_room=start_room)


def dispatch(engine: GameEngine, verb: str, target: str | None = None) -> str:
    """Dispatch a command directly through the engine's registry.

    Parameters
    ----------
    engine : GameEngine
        Engine whose registry handles the command.
    verb : str
        Command verb (e.g. ``"look"``, ``"forward"``).
    target : str or None, optional
        Optional noun target for the verb.

    Returns
    -------
    str
        Response text from the handler.
    """
    return engine.registry.dispatch(Command(verb, target), engine.state)


def describe_mock(engine: GameEngine) -> Mock:
    """Return the mocked room-description method attached by :func:`make_engine`.

    Parameters
    ----------
    engine : GameEngine
        Engine created with ``mock_describe=True``.

    Returns
    -------
    unittest.mock.Mock
        The mock standing in for ``describe_current_room``.
    """
    return cast(Mock, engine.describe_current_room)
