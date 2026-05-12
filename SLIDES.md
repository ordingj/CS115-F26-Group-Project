# Final Exam: Room 314

CS115 S26 Group Project  
Joseph Ording, Raj, Jerry, Matthew

---

## Project Summary

- Timed text adventure about reaching Room 314 before a final exam starts.
- Every command advances the clock, so puzzle solving and navigation both matter.
- The route is not a fixed map: players infer the correct path from environmental clues.
- The game supports a curses split-pane UI by default and a plain-text fallback for terminals
  without curses support.

---

## Game Features

- 10-minute timed adventure where every command costs time and raises pressure.
- Direction-based exploration with movement, observation, interaction, inventory, help, and
  quit/exit commands.
- Multi-step puzzle path: randomized 4-way clue, bathroom handwashing puzzle, mirror clue,
  janitor song clue, and final hallway choice.
- Wrong turns trigger randomized atmospheric detour rooms, then loop the player back with fresh
  clues.
- Environmental storytelling through YAML-driven rooms, signs, events, puzzle text, and song
  lyrics.
- Built-in inventory flavor for the watch, backpack, phone, keys, and wallet.
- Two playable interfaces: curses split-pane UI with live room/event panels and a plain-text
  fallback mode.
- Multiple outcomes: normal win, weird early ending, timeout loss, plus replay/exit prompt at
  the end.

---

## Core Gameplay Loop

1. Read the randomized clue at the four-way intersection.
2. Reach the bathroom junction and solve the handwashing puzzle.
3. Use the mirror clue to find the janitor hallway.
4. Listen to the janitor's song clue for the final left/right turn.
5. Reach Room 314 before the timer expires for the normal or weird ending.

---

## Architecture Overview

- `game/main.py` is the composition root: it loads data, builds the world, registers commands,
  and selects the UI.
- `data/*.yaml` holds player-facing narrative text, room definitions, commands, events, puzzle
  clues, and song data.
- `game/` is split by responsibility into `commands/`, `puzzles/`, `engine/`, plus shared
  state/world/event modules.
- The plain-text engine and curses engine share the same command pipeline and puzzle logic.

---

## Runtime Design

- `GameState` stores time remaining, location, puzzle progress, clue values, flags, and
  randomized detour history.
- `commands/player_commands.py` and `commands/player_movement.py` separate verb registration
  from movement and puzzle-routing logic.
- Puzzle-specific behavior lives with its owning domain modules under `game/puzzles/`.
- `engine/engine.py` and `engine/curses_engine.py` reuse shared room-view and command- dispatch
  behavior so both interfaces stay consistent.

---

## Agentic Coding Approach

- Work was driven from `TODO.md`, with one active task tracked at a time.
- Documentation stayed in sync with implementation through `README.md`, `ARCHITECTURE.md`, and
  `CHANGELOG.md` updates alongside code changes.
- Large refactors were handled in small validated slices: identify an owning module, simplify
  one path, update callsites, then remove redundant helpers.
- The goal was maintainability over shortcuts: fewer overlapping helpers, clearer module
  ownership, and no legacy fallback layers left behind.

---

## Testing Strategy

- `make test` runs the full unittest suite across command handling, puzzle flow, world
  building, endings, events, and curses helpers.
- `make coverage` enforces an 80% statement-coverage floor for `game/main.py` and the runtime
  modules under `game/`, `game/commands/`, `game/engine/`, and `game/puzzles/`.
- Tests are split by responsibility, with focused helper suites and end-to-end flow coverage.
- Refactors were validated with narrow tests first, then the broader project commands.

---

## Key Takeaways

- Data-driven content kept narrative and gameplay text out of Python code.
- Shared engine logic allowed two UIs without duplicating game rules.
- Puzzle systems were easier to evolve because Step 1, Step 2, and Step 3 logic each live in
  clear owning modules.
- Randomized clues and detours make the experience replayable while staying testable.
- YAML-backed content makes it easier to add or revise rooms, events, and clues without
  rewriting core logic.
- Focused unit tests made it safe to refactor behavior without breaking puzzle flow or endings.
- Keeping README, architecture notes, changelog, and TODOs aligned reduced confusion during
  development.
- The final codebase emphasizes maintainability, modular ownership, and regression coverage.
