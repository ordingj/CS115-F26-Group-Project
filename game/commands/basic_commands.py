"""Registration helpers for simple command handlers.

These handlers only depend on command-response text plus the current
``GameState``; they do not need live room or engine access.
"""

from __future__ import annotations

from typing import Any

from game import format_indented_lines
from game.commands.command import (
    CommandRegistry,
    register_target_state_command_specs,
    TargetStateCommandSpec,
    TargetStateHandler,
)
from game.state import GameState


def register_basic_commands(registry: CommandRegistry, cmd: dict[str, Any]) -> None:
    """Register simple stateless and inventory commands with *registry*.

    Covers ``check``, ``open``, ``knock``, ``inventory`` (alias ``i``),
    ``drop``, ``help``, and ``quit`` (alias ``exit``).

    Parameters
    ----------
    registry : CommandRegistry
        The registry to populate.
    cmd : dict[str, Any]
        Top-level ``responses`` mapping loaded from ``data/commands.yaml``.
    """

    def make_target_required_handler(
        command_key: str, response_key: str
    ) -> TargetStateHandler:
        """Return one handler that requires a target before formatting a response."""

        def handle_target_required(target: str | None, _state: GameState) -> str:
            """Return the no-target prompt or the formatted target response."""
            if target is None:
                return cmd[command_key]["no_target"]
            return cmd[command_key][response_key].format(target=target)

        return handle_target_required

    def handle_check(target: str | None, state: GameState) -> str:
        """Report time remaining, or deflect if a non-watch/time target is given."""
        if target in (None, "watch", "time"):
            return cmd["check"]["watch"].format(time=state.formatted_time())
        if target == "phone":
            return cmd["check"]["phone"]
        return cmd["check"]["other"].format(target=target)

    handle_open = make_target_required_handler("open", "blocked")
    handle_knock = make_target_required_handler("knock", "no_answer")

    def handle_inventory(_target: str | None, state: GameState) -> str:
        """List the items the player is currently carrying."""
        if not state.inventory:
            return cmd["inventory"]["empty"]
        return (
            cmd["inventory"]["list_prefix"]
            + "\n"
            + format_indented_lines(state.inventory)
        )

    def handle_drop(_target: str | None, _state: GameState) -> str:
        """Refuse to drop anything — the player needs to keep all items."""
        return cmd["inventory"]["drop"]

    def handle_help(_target: str | None, _state: GameState) -> str:
        """Return a formatted list of available commands and their syntax."""
        help_text = cmd["help"]
        return help_text["header"] + "\n" + format_indented_lines(help_text["entries"])

    def handle_quit(_target: str | None, state: GameState) -> str:
        """End the session gracefully; suppress the timeout losing screen."""
        state.quit = True
        state.game_over = True
        return cmd["quit"]["farewell"]

    command_specs: tuple[TargetStateCommandSpec, ...] = (
        (("check",), handle_check),
        (("open",), handle_open),
        (("knock",), handle_knock),
        (("inventory", "i"), handle_inventory),
        (("drop",), handle_drop),
        (("help",), handle_help),
        (("quit", "exit"), handle_quit),
    )

    register_target_state_command_specs(registry, command_specs)
