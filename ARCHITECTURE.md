# Architecture

## Overview

Final Exam: Room 314 is a data-driven text adventure. The Python code owns control flow, state
transitions, and rendering, while YAML files hold room definitions, player-facing text, event
specs, and janitor song data.

At startup, `game/main.py` builds the world, game state, command registry, and event queue,
then selects either the default curses UI or the plain-text engine.

## Runtime flow

1. `game/main.py` loads YAML-backed data and constructs fresh room objects with
   `build_world()`.
2. `GameState` tracks location, time remaining, puzzle progress, clue values, flags, the
   randomized interstitial rooms already consumed this play-through, and end conditions.
3. `game/player_commands.py` owns `build_commands()`, which registers every player verb and
   closes over the live engine reference so handlers can inspect rooms and mutate state.
   Movement registration is delegated to `game/player_movement.py`, where puzzle routing,
   room-entry side effects, and movement validation live behind a dedicated helper layer. The
   remaining command handlers now route room-gated verbs through shared adapters in
   `game.command`, while both the room-target `look`/`read` verbs and the room-gated
   bathroom/janitor verbs are registered from shared spec loops so `game/player_commands.py`
   stays focused on behavior plus fallbacks instead of duplicating parallel registration
   blocks.
4. `GameEngine` owns the shared event/input/dispatch/tick loop through overridable I/O hooks,
   and `CursesEngine` reuses that loop after its curses-specific setup so both UIs follow the
   same command pipeline before the timer advances.
5. End-state handling chooses the normal win, weird win, lose, or quit path based on the final
   `GameState`.

## Code structure

- `game/__init__.py`: shared package helpers, including the central YAML asset loader and small
  shared text-formatting helpers.
- `game/main.py`: composition root, CLI parsing, and UI selection.
- `game/commands/basic_commands.py`: simple stateless and inventory command registrations
  shared by the composition root; check/help/inventory/quit keep their small response logic
  local, while the target-required `open`/`knock` verbs share one small response factory plus
  the shared simple-command batch registration helper from `game.commands.command`.
- `game/puzzles/bathroom.py`: bathroom Step 2 shared state snapshot API, mirror-direction roll,
  response-key lookup, exit-block rule, and action-state-machine helpers, including wash-phase
  transitions, retry counters, clean-hands short-circuiting, the shared action-dispatch helper
  used by `soap`, `rinse`, and `stop`, plus the declarative bathroom action command specs
  consumed by `game/commands/player_commands.py`.
- `game/puzzles/bathroom_view.py`: read-only Step 2 bathroom helpers for sink inspection,
  revealed mirror-clue text, and ambient status text, plus the bathroom room-target command
  handlers consumed by `game/commands/player_commands.py`.
- `game/puzzles/intersection.py`: Step 1 four-way intersection clue generation, return-aware
  room description, clue-formatting helpers, and clue-specific read-target handlers consumed by
  the movement entry path, command builder, and the engine's dynamic room view.
- `game/puzzles/janitor.py`: Step 3 janitor song-pool loading, clue roll/formatting helpers
  built on the shared left/right direction-roll utility, one shared `janitor_text()` formatter
  used by both the ambient hallway clue path and the janitor-hallway `listen` command, and the
  declarative janitor command spec consumed by `game/commands/player_commands.py`.
- `game/commands/player_commands.py`: command builder plus room-target, bathroom-action, and
  janitor interaction handlers, with table-driven room-target plus room-gated command
  registrations, shared room-aware registry adapters from `game.commands.command`, and
  bathroom/janitor-specific command fragments delegated to the owning domain modules instead of
  being bound locally.
- `game/commands/player_movement.py`: the full directional movement pipeline, including
  movement command registration, special blocker responses, direction-gated puzzle validation,
  wrong-way detour wiring, move commits, configured room-entry setup for puzzle and
  interstitial detour rooms, a stateful flavor-room sampler that prefers unused randomized
  detour rooms until the eligible pool is exhausted, and named puzzle-rule specs for the
  direction-gated routing branches, with direct `(engine, state)` room-entry hooks and named
  late-bound roll/random helpers that preserve the current test patch points.
- `game/engine/curses_rendering.py`: shared curses-only panel layout, room-panel section
  assembly, line-wrapping, and style helpers used by `CursesEngine`.
- `game/commands/command.py`: command parsing, handler registration/dispatch, and the shared
  adapters for simple `(target, state)` handlers, room-aware command handlers, plus
  fixed-response and state-only room-target helpers used by declarative command specs,
  including shared batch registration helpers for simple, room-target, and room-gated command
  families.
- `game/state.py`: mutable game session state, randomized-detour history, and clock
  bookkeeping.
- `game/room.py`: room dataclass and deep-clone helper for fresh sessions.
- `game/world.py`: loads `data/rooms.yaml` and exports the room graph plus flavor-room pool.
- `game/puzzles/puzzle.py`: shared active-clue storage and direction-matching utilities reused
  across the intersection, bathroom, janitor, and movement-validation paths.
- `game/event.py`: declarative event conditions plus table-driven YAML condition loading, with
  one shared spec-to-builder path used by every supported condition type.
- `game/engine/engine.py`: plain-text renderer, intro/end frame helper, shared
  room-presentation helpers, the shared runtime play loop, and ending screens.
- `game/engine/curses_engine.py`: curses-based split-pane renderer layered on top of
  `GameEngine`, overriding only the presentation hooks needed to reuse the shared runtime loop
  and routing both the log and room panels through one shared boxed-panel render helper.

## Data files

- Runtime modules load YAML assets through `game.load_yaml_data()` so file-path and parsing
  logic stays centralized.
- `data/rooms.yaml`: fixed rooms, flavor rooms, exits, items, and room attributes.
- `data/commands.yaml`: player-facing command responses, shared UI labels, ending text, and CLI
  help strings.
- `data/events.yaml`: ambient and timed narrative events declared as condition specs.
- `data/puzzle.yaml`: clue templates, Step 1 readable-target aliases, and bathroom mirror-clue
  formatting strings.
- `data/songs.yaml`: left/right song pools for the janitor clue.

## Puzzle progression

1. Four-way intersection: `game.intersection.step1_roll()` picks a clue type and correct
   direction.
2. Wrong turn handling: the player is routed through randomized flavor rooms before returning
   to the four-way with a fresh clue, and those detours prefer rooms not yet used elsewhere in
   the current play-through.
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
- The curses input bar polls once per second while waiting for input so the header countdown
  can stay live; the timer keeps the normal 15-second action penalty and shifts from the
  default header color to yellow below five minutes and red below one minute remaining.
- `GameEngine._current_room_view()` centralizes dynamic room-description tweaks, clue, exits,
  visible-items, and timer assembly so both UIs consume the same room data before applying
  their own formatting.
- `CursesEngine` owns the curses run loop, window lifecycle, input prompt, and transition
  effects, while `game/curses_rendering.py` owns boxed-panel rendering, room-panel line
  assembly, and style classification helpers.
- Both UIs share the same command handlers, event queue, puzzle logic, and end-state rules.

## Testing strategy

- `tests/helpers.py` provides shared engine builders so the main test modules reuse identical
  world/state/registry setup. Plain-engine builders mock room rendering by default; rendering
  tests opt back into the real `describe_current_room()` path when needed, helper suites reuse
  shared bathroom/intersection fixtures from the same module, and flow suites reuse shared
  dispatch helpers there as well.
- `tests/check_coverage_threshold.py` is a lightweight coverage harness used by
  `make coverage`. It loads the `.coverage` data file after the unittest run and enforces an
  80% minimum statement-coverage threshold for every shipped runtime module in `game/main.py`,
  `game/*.py`, `game/commands/*.py`, `game/engine/*.py`, and `game/puzzles/*.py`.
- `tests/test_core_helpers.py` covers parser behavior, registry dispatch, state helpers, and
  shared YAML loading, plus composition-root startup wiring in `game/main.py`.
- `tests/test_puzzle_helpers.py` covers puzzle helpers, bathroom helpers, and janitor helpers.
- `tests/test_engine_helpers.py` covers shared engine-formatting helpers and plain-engine loop
  behavior.
- `tests/test_curses_helpers.py` covers curses-only formatting helpers and `CursesEngine`
  helper methods.
- `tests/test_event_helpers.py` covers declarative event condition loading and `EventQueue`
  behavior.
- `tests/test_command_flow.py` covers supported commands, edge-case command handling, and
  inventory command behavior.
- `tests/test_puzzle_flow.py` covers navigation, blocked exits, puzzle progression, and win
  routing.
- `tests/test_endings.py` covers end-state selection and ending output rendering.
- `tests/test_world.py` protects room cloning and the shipped base room graph.
- `tests/TESTS.md` is the operator-facing guide for choosing the right suite, running focused
  versus full validation, and interpreting coverage-threshold failures.

## Documentation workflow

`TODO.md` tracks active work, `CHANGELOG.md` records completed changes, `README.md` targets
players and graders, `SLIDES.md` captures the presentation-ready project summary, and
`DEVELOPER.md` describes setup and contributor workflow. Keep those documents in sync whenever
gameplay, tooling, or project-facing materials change.
