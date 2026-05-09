# Architecture

## Overview

Final Exam: Room 314 is a data-driven text adventure. The Python code owns control flow, state
transitions, and rendering, while YAML files hold room definitions, player-facing text, event
specs, and janitor song data.

At startup, `main.py` builds the world, game state, command registry, and event queue, then
selects either the default curses UI or the plain-text engine.

## Runtime flow

1. `main.py` loads YAML-backed data and constructs fresh room objects with `build_world()`.
2. `GameState` tracks location, time remaining, puzzle progress, clue values, flags, and end
   conditions.
3. `game/player_commands.py` owns `build_commands()`, which registers every player verb and
   closes over the live engine reference so handlers can inspect rooms and mutate state.
   Movement registration is delegated to `game/player_movement.py`, where puzzle routing,
   room-entry side effects, and movement validation live behind a dedicated helper layer. The
   remaining command handlers normalize room-gated and room-target behavior through the shared
   `game.command.register_target_state_handler(...)` adapter, direct current-room checks, and
   room/target dispatch tables instead of stacking extra private forwarding wrappers around the
   same engine lookup and branch logic.
4. `GameEngine` or `CursesEngine` runs the input loop: fire ambient events, parse input,
   dispatch a command, print/log any response, then advance the timer.
5. End-state handling chooses the normal win, weird win, lose, or quit path based on the final
   `GameState`.

## Code structure

- `game/__init__.py`: shared package helpers, including the central YAML asset loader and small
  shared text-formatting helpers.
- `game/basic_commands.py`: simple stateless and inventory command registrations shared by the
  composition root; each verb now keeps its small response logic inline while still reusing the
  shared target/state adapter from `game.command`.
- `game/bathroom.py`: bathroom puzzle helpers for ambient status clues, mirror/sink inspection,
  exit blocking, and handwashing state transitions.
- `game/janitor.py`: shared janitor song-clue formatting helpers consumed directly by the
  engine's ambient hallway clue path and the `LISTEN` command.
- `game/player_commands.py`: command builder plus room-target, bathroom-action, and janitor
  interaction handlers, with direct room-gated registrars and `functools.partial`-bound
  bathroom actions instead of extra wrapper helpers.
- `game/player_movement.py`: movement command registration, wrong-way handling, puzzle-step
  validation, and move-commit plumbing, including bound arrival callbacks that feed the shared
  room-entry router without extra forwarding closures.
- `game/movement_routing.py`: dynamic room-entry routing, roll-once puzzle seeding, and
  clue-driven exit rewiring for puzzle rooms, including data-driven specs for clue-routed room
  entry handlers.
- `game/movement_validation.py`: shared movement rule tables, special blocker responses, and
  direction-gated puzzle validation helpers.
- `game/curses_rendering.py`: shared curses-only panel layout, line-wrapping, and style helpers
  used by `CursesEngine`.
- `main.py`: composition root, CLI parsing, and UI selection.
- `game/command.py`: command parsing, handler registration/dispatch, and the shared adapter for
  simple `(target, state)` command handlers.
- `game/state.py`: mutable game session state and clock bookkeeping.
- `game/room.py`: room dataclass and deep-clone helper for fresh sessions.
- `game/world.py`: loads `data/rooms.yaml` and exports the room graph plus flavor-room pool.
- `game/puzzle.py`: randomized clue generation and clue-formatting helpers, including one
  shared roll-and-store helper reused across Step 1/2/3 clue seeding.
- `game/event.py`: declarative event conditions plus table-driven YAML condition loading.
- `game/engine.py`: plain-text renderer, intro, shared room-presentation helpers, and ending
  screens.
- `game/curses_engine.py`: curses-based split-pane renderer layered on top of `GameEngine`.

## Data files

- Runtime modules load YAML assets through `game.load_yaml_data()` so file-path and parsing
  logic stays centralized.
- `data/rooms.yaml`: fixed rooms, flavor rooms, exits, items, and room attributes.
- `data/commands.yaml`: player-facing command responses, UI strings, and ending text.
- `data/events.yaml`: ambient and timed narrative events declared as condition specs.
- `data/puzzle.yaml`: clue templates for the four-way intersection and bathroom mirror.
- `data/songs.yaml`: left/right song pools for the janitor clue.

## Puzzle progression

1. Four-way intersection: `step1_roll()` picks a clue type and correct direction.
2. Wrong turn handling: the player is routed through randomized flavor rooms before returning
   to the four-way with a fresh clue.
3. Bathroom puzzle: command handlers mutate `wash_phase`, `sink_running`, and soap state until
   the mirror clue becomes visible.
4. Restroom exit node: the mirror clue rewires the next junction toward the janitor hallway.
5. Janitor hallway: `step3_roll()` selects a song whose lyrics imply the final left/right turn,
   and `listen` simply formats that already-seeded clue.
6. Final stretch: entering `room_314` sets the win state; the timer determines normal vs weird
   ending text.

## UI layers

- Plain-text mode prints room descriptions and command responses to stdout.
- Curses mode shows a header, boxed LOCATION/ACTIVITY panels, color-coded command/event/log
  output, and a one-line input prompt.
- `GameEngine._current_room_view()` centralizes dynamic clue, exits, visible-items, and timer
  assembly so both UIs consume the same room data before applying their own formatting.
- `CursesEngine` owns the curses run loop, window lifecycle, input prompt, and transition
  effects, while `game/curses_rendering.py` owns boxed-panel rendering, room-panel line
  assembly, and style classification helpers.
- Both UIs share the same command handlers, event queue, puzzle logic, and end-state rules.

## Testing strategy

- `tests/helpers.py` provides shared engine builders so the main test modules reuse identical
  world/state/registry setup. Plain-engine builders mock room rendering by default; rendering
  tests opt back into the real `describe_current_room()` path when needed, and flow suites
  reuse shared dispatch helpers from the same module.
- `tests/check_coverage_threshold.py` is a lightweight coverage harness used by
  `make coverage`. It loads the `.coverage` data file after the unittest run and enforces an
  80% minimum statement-coverage threshold for every shipped runtime module (`main.py` plus
  `game/*.py`).
- `tests/test_core_helpers.py` covers parser behavior, registry dispatch, state helpers, and
  shared YAML loading, plus composition-root startup wiring in `main.py`.
- `tests/test_puzzle_helpers.py` covers puzzle helpers, bathroom helpers, and janitor helpers.
- `tests/test_ui_event_helpers.py` covers shared engine-formatting helpers, curses-only
  formatting helpers, `CursesEngine` helper methods, and declarative event condition loading.
- `tests/test_command_flow.py` covers supported commands, edge-case command handling, and
  inventory command behavior.
- `tests/test_puzzle_flow.py` covers navigation, blocked exits, puzzle progression, and win
  routing.
- `tests/test_endings.py` covers end-state selection and ending output rendering.
- `tests/test_world.py` protects room cloning and the shipped base room graph.

## Documentation workflow

`TODO.md` tracks active work, `CHANGELOG.md` records completed changes, `README.md` targets
players and graders, and `DEVELOPER.md` describes setup and contributor workflow. Keep all four
in sync whenever gameplay or tooling changes.
