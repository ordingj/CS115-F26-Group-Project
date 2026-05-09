# Changelog

## 2026-05-08

- Tests — raise source coverage for `main.py`, `game/engine.py`, `game/curses_rendering.py`,
  and `game/curses_engine.py` with composition-root tests plus mock-driven engine/curses helper
  coverage, so the new `make coverage` gate can enforce the 80% per-file threshold.

- Tooling — add a `make coverage` workflow backed by `coverage.py` plus
  `tests/check_coverage_threshold.py`, so the project can enforce an 80% minimum per-file
  statement-coverage threshold across `main.py` and `game/*.py` during `make all coverage`.

- Refactor — simplify `game/engine.py::_current_room_clue()` by replacing its per-call
  room-id/lambda dispatch table with direct branching, and deduplicate the repeated
  intersection-room setup in `tests/test_ui_event_helpers.py` through one shared helper.
  Focused `tests.test_ui_event_helpers` passes.

- Refactor — simplify `game/player_commands.py` by collapsing the room-gated and room-target
  registration flow into direct current-room checks plus direct dispatch lookups, and bind the
  bathroom verbs with `functools.partial` instead of an extra bathroom-action wrapper helper.
  Focused command-flow and puzzle-flow suites pass.

- Refactor — inline the thin target-required and indented-list helper factories in
  `game/basic_commands.py` so `open`, `knock`, `inventory`, and `help` register direct local
  handlers, and bind movement arrival callbacks with `functools.partial` in
  `game/player_movement.py` instead of an inline forwarding lambda. Strengthen
  `tests.test_puzzle_flow` so the Step 2 entry test proves patched roll seeding still applies.

- Refactor — data-drive clue-routed room-entry handler wiring in `game/movement_routing.py`
  through one shared spec table that builds partial handlers for `intersection_3way_exit` and
  `hallway_janitor`, replacing duplicated manual partial setup blocks. Focused
  `tests.test_puzzle_flow` passes.

- Refactor — consolidate duplicated clue roll-and-store plumbing in `game/puzzle.py` through
  one shared helper used by Step 1/2/3 roll flows, replacing repeated random-choice and
  `active_clues` assignment logic. Focused puzzle helper/flow tests pass.

- Refactor — centralize the shared target/state command-registration adapter in
  `game/command.py` and reuse it from `game/basic_commands.py` and `game/player_commands.py`
  instead of keeping duplicate registry wrapper helpers in both modules. Focused command/core
  helper tests pass.

- Refactor — move bathroom status clue logic out of `game/engine.py` and into
  `game/bathroom.py` so the Step 2 state machine owns its own ambient clue text, and
  consolidate repeated `BathroomHelpersTest` setup into `setUp()`. Focused bathroom/UI helper
  tests pass.

- Refactor — centralize the shared two-space line-formatting helper in `game/__init__.py` and
  reuse it from `game/basic_commands.py` and `game/janitor.py` instead of keeping separate
  indentation loops in each module. Focused janitor and command-flow tests pass.

- Refactor — consolidate the duplicated janitor clue formatting flow in `game/janitor.py`
  through one shared helper used by both `janitor_hint_text()` and `janitor_listen_text()`.
  Focused `tests.test_puzzle_helpers.JanitorHelpersTest` passes.

- Refactor — remove the stale engine-local janitor hint wrapper from `game/engine.py` so the
  hallway clue dispatch calls `game/janitor.py` directly, and add engine-facing regression
  coverage in `tests.test_ui_event_helpers`. Focused janitor/UI helper tests pass.

- Refactor — consolidate the duplicated style-to-attribute dispatch in
  `game/curses_rendering.py` through one shared style-map helper used by both `log_attr()` and
  `room_attr()`. Focused `tests.test_ui_event_helpers` passes.

- Refactor — normalize `game/basic_commands.py` through one shared target/state registration
  adapter so the simple command handlers only declare the arguments they actually use instead
  of each carrying the full registry signature. Focused `tests.test_command_flow` passes.

- Refactor — remove the single-use room-target handler factories from `game/player_commands.py`
  and replace them with the direct local handlers they were creating for lobby sign and
  bathroom mirror/sink dispatch. Focused command-flow and bathroom target-routing tests pass.

- Refactor — remove the private `_clue_routed_entry_handler` wrapper from
  `game/movement_routing.py` and bind `_enter_clue_routed_room(...)` directly with
  `functools.partial` for the clue-routed entry table. Focused `tests.test_puzzle_flow` passes.

- Refactor — data-drive the field-based event condition builders in `game/event.py` through one
  shared parser factory instead of repeating near-identical lambdas for move count, location,
  and wrong-turn checks. Focused `tests.test_ui_event_helpers` passes.

- Refactor — simplify `game/player_commands.py` command registration by routing room-gated and
  room-target verbs through one shared target/state adapter instead of repeating separate
  registry wrapper closures. Focused `tests.test_command_flow` passes.

- Documentation — create `data/DATA.md`, a comprehensive catalog of every YAML data file.
  Covers `commands.yaml` (all response-key tables with placeholder tokens and phase mappings),
  `rooms.yaml` (room entry structure, exit-value reference, structural vs. flavor room tables,
  attributes and items keys), `events.yaml` (condition-type reference and full event catalog),
  `puzzle.yaml` (clue-type keys and placeholder tokens), and `songs.yaml` (entry structure,
  direction values, and full song title lists).

## 2026-05-11

- Documentation — thorough numpy-style docstring pass across every Python source file and test.
  Every public and private function, method, and type alias now has numpy-style sections
  (`Parameters`, `Returns`, `Raises`, `Attributes`) where applicable, plus copious inline
  comments explaining complex logic and design decisions. Covered files: `game/__init__.py`,
  `game/command.py`, `game/state.py`, `game/room.py`, `game/world.py`, `game/puzzle.py`,
  `game/event.py`, `game/engine.py`, `game/curses_engine.py`, `game/curses_rendering.py`,
  `game/basic_commands.py`, `game/bathroom.py`, `game/janitor.py`, `game/player_commands.py`,
  `game/player_movement.py`, `game/movement_routing.py`, `game/movement_validation.py`,
  `tests/helpers.py`, and all `tests/test_*.py` modules. Full suite passes.

## 2026-05-10

- Documentation — complete documentation pass across all Python source files and tests. Added
  docstrings to six inner-closure functions (`handle_static_target`, `handle_mirror_target`,
  `handle_sink_target`, `handle_room_only_action`, `handle_room_target_command` in
  `game/player_commands.py`; `handle_clue_routed_entry` in `game/movement_routing.py`) and to
  all test methods across five test modules (`test_command_flow.py`, `test_core_helpers.py`,
  `test_endings.py`, `test_puzzle_helpers.py`, `test_puzzle_flow.py`,
  `test_ui_event_helpers.py`).

- Refactor — move all hardcoded curses UI label strings out of Python and into
  `data/commands.yaml`. A new `responses.ui_labels` section holds the header time prefix, panel
  titles (LOCATION, ACTIVITY), and room-panel section headings (DETAILS, CLUE, EXITS, YOU
  NOTICE). `game/curses_engine.py` and `game/curses_rendering.py` now read these values via the
  shared `UI` dict. Full suite passes.

- Documentation — update `README.md` with Python 3.12+ requirement and a step-by-step venv
  setup section. Update `DEVELOPER.md` with the Python 3.12+ requirement heading.

## 2026-05-09

- Refactor — extract `_end_lines()` to `GameEngine` in `game/engine.py`. Both
  `GameEngine._handle_end()` and `CursesEngine._handle_end()` contained identical logic for
  selecting the end-screen key (won_early / won / lost / quit). The shared selection now lives
  in one place; each override calls `_end_lines()` and handles only its own rendering. Full
  suite passes.

- Refactor — inline `_intersection_clue` into `_current_room_clue` in `game/engine.py`. The
  two-line private method was only referenced once, via the clue-handler dispatch dict. It is
  replaced with `lambda: step1_clue_text(self.state)` directly in the dict, removing a trivial
  single-use wrapper. Full suite passes.

- Refactor — promote `room_target_handler` from a local variable inside `build_commands()` to a
  module-level alias `_RoomTargetHandler` in `game/player_commands.py`. The alias is now
  consistent with the `RoomEntryHandler` and `WrongWayHandler` conventions in
  `game/movement_routing.py` and `game/movement_validation.py`. Full suite passes.

- Refactor — remove the `_wrong_way_response` adapter in `game/player_movement.py`. The
  `_bounce_wrong_way` helper now accepts `wrong_turn_flag` as a regular optional positional
  parameter so it matches the `WrongWayHandler` interface directly and can be passed to
  `puzzle_move_response` without a thin forwarding wrapper. Full suite passes.

- Refactor — inline `_wire_clue_route` into `_enter_clue_routed_room` in
  `game/movement_routing.py`. The private helper was only ever called from
  `_enter_clue_routed_room`; folding its five-line body in removes a dead indirection layer
  without changing any behaviour. Full suite passes.

- Modernize typing imports across five modules — replace deprecated `typing.Optional[X]` with
  `X | None` syntax and move `Callable`/`Mapping` imports from `typing` to `collections.abc` in
  `game/engine.py`, `game/command.py`, `game/room.py`, `game/bathroom.py`, and `game/event.py`.
  All remaining files already used the modern forms. Full suite passes.

## 2026-05-08 (Earlier Entries)

- Refactor — split the movement validation helpers out of `game/player_movement.py` into
  `game/movement_validation.py`. Special blocker responses and direction-gated puzzle rules now
  live in a dedicated module while movement registration stays focused on the final move path.
  Focused puzzle-flow tests pass.

- Refactor — split the room-entry routing helpers out of `game/player_movement.py` into
  `game/movement_routing.py`. Movement registration now stays focused on command wiring,
  direction validation, and move commits while dynamic puzzle-room routing lives in a dedicated
  module. Focused puzzle-flow tests pass.

- Refactor — split the rendering helper surface out of `game/curses_engine.py` into
  `game/curses_rendering.py`. The curses engine now stays focused on the run loop, windows,
  input, and transitions while deterministic panel/style helpers live in a dedicated module.
  Focused UI helper tests pass.

- Refactor — split the aggregated flow suite out of `tests/test_game_flow.py`. Command
  coverage, puzzle/navigation flow, and ending checks now live in focused modules that reuse
  one shared flow-test helper surface. Focused flow-module tests pass.

- Refactor — split the oversized helper test module out of `tests/test_logic_helpers.py`. The
  parser/state/loader checks, puzzle-domain checks, and UI/event checks now live in three
  focused test modules under the 500-line target. Focused helper-module tests pass.

- Refactor — split the oversized movement flow out of `game/player_commands.py` into
  `game/player_movement.py`. Movement verbs, puzzle routing, wrong-way handling, and room-entry
  side effects now live in a dedicated module while `build_commands()` stays focused on
  non-movement command registration. Focused command-flow tests pass.

- Refactor — share clue-routed room-entry handler registration in `game/player_commands.py`.
  The post-bathroom and janitor entries now use one factory-backed registration helper instead
  of thin wrapper functions that only forwarded constants into `_enter_clue_routed_room(...)`.
  Focused command-flow tests pass.

- Refactor — share room-only command registration in `game/player_commands.py`. Bathroom
  actions and the janitor `listen` command now reuse one room-only registration helper instead
  of repeating their own required-room handler glue. Focused command-flow tests and the full
  suite pass.

- Refactor — share room-target command registration in `game/player_commands.py`. The `look`
  and `read` commands now reuse one room-target-first registration helper instead of each
  rebuilding the same dispatch-then-fallback handler shape. Focused command-flow tests and the
  full suite pass.

- Refactor — share clue-routed room-entry wiring in `game/player_commands.py`. The
  post-bathroom and janitor entry helpers now reuse one optional seed-and-wire helper instead
  of repeating the same `_wire_clue_route(...)` setup shape. Focused movement/puzzle-flow tests
  and the full suite pass.

- Refactor — table-drive special move blocker responses in `game/player_commands.py`.
  `handle_move()` now routes the lobby blocker sentinels through one response map instead of
  repeating direct destination checks inline. Focused movement/puzzle-flow tests and the full
  suite pass.

- Refactor — table-drive puzzle move validation in `game/player_commands.py`. `handle_move()`
  now loops over shared Step 1 and Step 3 rule definitions instead of repeating the same
  `_validate_direction_puzzle_move(...)` call shape twice. Focused movement/puzzle-flow tests
  and the full suite pass.

- Refactor — share room-only command gating in `game/player_commands.py`. Bathroom actions and
  the janitor `listen` command now reuse one required-room gate instead of each repeating their
  own missing-room fallback flow. Focused command-flow tests and the full suite pass.

- Refactor — share the bathroom sink target handler in `game/player_commands.py`. The `look`
  dispatch table now reuses a sink handler factory instead of keeping the last inline
  room-target lambda. Focused command-flow tests and the full suite pass.

- Refactor — share bathroom action handler registration in `game/player_commands.py`. The
  rinse, stop, and soap commands now reuse one registration helper instead of each defining the
  same delegate wrapper before registration. Focused command-flow tests and the full suite
  pass.

- Refactor — share repeated room-target response handlers in `game/player_commands.py`. The
  `look` and `read` dispatch tables now reuse small mirror/static handler factories instead of
  rebuilding the same lambdas inline. Focused command-flow tests and the full suite pass.

## 2026-05-07

- Refactor — share the duplicated test-engine setup in `tests/helpers.py`. The plain and curses
  test builders now reuse one internal engine factory instead of each repeating the same world,
  state, registry, and engine-reference setup. Focused command/helper tests and the full suite
  pass.

- Refactor — split the command builder into `game/player_commands.py`. `main.py` now stays
  focused on startup and UI selection while the player command wiring lives in a dedicated game
  module. Updated command-heavy tests, shared test builders, and architecture docs; focused
  command/helper tests and the full suite pass.

- Refactor — remove the thin flow-test engine wrapper in `tests/test_game_flow.py`. The flow
  suite now uses the shared test builder in `tests/helpers.py` directly, with mocked room
  rendering handled by the shared helper and the rendering-specific helper tests opting out.
  Focused command/helper tests and the full suite pass.

- Refactor — share active janitor chorus-line extraction in `game/janitor.py`. The ambient
  janitor hint and `LISTEN` helper now reuse one clue-line reader instead of each repeating the
  same active-clue lookup and line splitting. Focused janitor-helper tests and the full suite
  pass.

- Refactor — consolidate repeated puzzle-step movement validation in `main.py`. `handle_move()`
  now reuses one helper for Step 1 and Step 3 direction checks instead of repeating the same
  wrong-way bounce and solved-state update flow inline. Focused movement/puzzle-flow tests and
  the full suite pass.

- Refactor — share clue-driven exit wiring in `main.py`. The bathroom exit node and janitor
  hallway now reuse one helper for clue-based route setup instead of each repeating the same
  active-clue lookup and `_route()` call shape. Focused movement/puzzle-flow tests and the full
  suite pass.

- Refactor — share clue-value retrieval in `game/puzzle.py`. The puzzle clue readers and
  direction checks now reuse one helper instead of repeating the same `active_clues` lookup and
  empty-string fallback path. Focused puzzle-helper tests and the full suite pass.

- Refactor — share the bathroom phase-transition response helper in `game/bathroom.py`. The
  Step 2 rinse and stop helpers now reuse one transition helper instead of repeating the same
  phase/sink mutation followed by a keyed response return. Focused bathroom-helper tests and
  the full suite pass.

- Refactor — centralize bathroom phase-state plumbing in `game/bathroom.py`. The Step 2 helper
  state machine now reuses shared phase readers and phase-plus-sink writers instead of
  repeating raw attribute lookups and paired assignments. Focused bathroom-helper tests and the
  full suite pass.

- Refactor — collapse the duplicated field-comparison helpers in `game/event.py`. The event
  builder map now reuses one generic field-condition factory instead of separate equality and
  lower-bound helpers with the same structure. Focused event-helper tests and the full suite
  pass.

- Refactor — share room-target dispatch for `look` and `read` in `main.py`. The command layer
  now routes room-specific target responses through one helper instead of repeating manual
  room-and-target branching in both handlers. Added direct game-flow coverage for bathroom
  `look` helpers and the `read detour_sign` alias.

- Refactor — share the roll-once room-entry helper in `main.py`. The bathroom and janitor room
  entry handlers now reuse one rolled-flag helper instead of each repeating the same roll-once
  control flow. Added a regression test covering puzzle-room revisits in
  `tests/test_game_flow.py`.

- Refactor — share the target-required command helper in `game/basic_commands.py`. The `open`
  and `knock` handlers now reuse one target-checking factory instead of each repeating the same
  control flow. Focused game-flow tests and the full suite pass.

- Refactor — share the indented list formatter in `game/basic_commands.py`. The `help` and
  `inventory` handlers now reuse one output helper instead of each rebuilding the same
  line-indented list format. Focused game-flow tests and the full suite pass.

- Refactor — centralize the shared already-clean guard in `game/bathroom.py`. The Step 2 action
  helpers now reuse one early-return helper instead of each repeating the same clean-state
  check. Added direct regression coverage for the already-clean path in
  `tests/test_logic_helpers.py`.

- Refactor — table-drive dynamic room-clue dispatch in `game/engine.py`. Special clue rendering
  for the four-way, bathroom, and janitor hallway now routes through a room-id handler map
  instead of another growing `if` chain. Focused engine helper tests and the full suite pass.

- Refactor — consolidate repetitive inventory assertions in `tests/test_game_flow.py`. The
  inventory drop and item-inspection checks now use `subTest` loops instead of near-identical
  one-off methods, keeping the same coverage with less duplicated test code. Focused game-flow
  tests and the full suite pass.

- Refactor — table-drive event condition construction in `game/event.py`. YAML condition types
  now dispatch through a builder map backed by shared comparison helpers instead of one growing
  `_build_condition()` switch. Focused event-helper tests and the full suite pass.

- Refactor — consolidate shared direction helper logic in `game/puzzle.py`. Step 2 mirror
  rolls, Step 3 song rolls, and the step-direction correctness checks now reuse shared
  left/right helper functions instead of repeating the same direction plumbing. Focused
  puzzle/game-flow tests and the full suite pass.

- Refactor — table-drive room-entry dispatch in `main.py`. Dynamic destination setup now uses a
  destination-to-handler mapping instead of a growing `if`/`elif` chain, reducing overlap in
  the command composition path. Focused command tests and the full suite pass.

- Refactor — centralize repeated command alias registration in `main.py`. Shared handlers for
  movement and verb aliases now register through one helper instead of repeating direct
  `registry.register()` calls. Focused command tests and the full suite pass.

- Refactor — centralize the bathroom-only command gate in `main.py`. The `rinse`, `stop`, and
  `soap` handlers now share one helper for bathroom room lookup and response selection instead
  of repeating the same control flow in three places. Focused bathroom/game-flow tests and the
  full suite pass.

- Refactor — extract shared test engine builders into `tests/helpers.py`. The helper-level and
  game-flow suites now reuse one engine-construction surface instead of maintaining
  near-identical setup code in both modules. Focused test-module validation and the full suite
  pass.

- Refactor — centralize janitor song formatting in `game/janitor.py`. The ambient hallway hint
  in `game/engine.py` and the `LISTEN` command in `main.py` now share the same
  chorus-formatting helper instead of each splitting and indenting lyric lines independently.
  Added focused helper-level coverage for the shared janitor formatter.

- Refactor — centralize bathroom puzzle behavior in `game/bathroom.py`. `main.py` now delegates
  bathroom exit blocking, mirror/sink inspection, and soap/rinse/stop state transitions to the
  shared helper module instead of repeating that logic across multiple command handlers. Added
  focused helper tests plus the existing game-flow integration coverage.

- Refactor — split the stateless/basic command registrations out of `main.py` into
  `game/basic_commands.py`, keeping `build_commands()` as the public composition point while
  bringing `main.py` back under the repository's 500-line threshold. The build/dispatch flow is
  still covered by the existing integration tests.

- Refactor — add shared live-engine/current-room helpers inside `build_commands()` so `LOOK`,
  `READ`, `RINSE`, `STOP`, `SOAP`, and `LISTEN` stop repeating the same engine lookup and
  room-guard boilerplate. Integration coverage for bathroom and janitor flows passes unchanged.

- Refactor — split `handle_move()` in `main.py` into smaller local helpers for wrong-way
  bounces, flavor-chain wiring, and destination-room setup. The movement handler now focuses on
  validation and puzzle-step decisions while post-move room configuration lives behind
  dedicated helpers. Existing game-flow integration tests cover the refactor unchanged.

- Code quality audit — removed the defensive Step 3 reroll from `handle_listen()` in `main.py`.
  Entering `hallway_janitor` remains the only path that seeds the janitor song clue, and the
  integration tests now verify that `LISTEN` consumes the clue already attached during hallway
  entry instead of mutating hidden state on demand.

- Refactor — centralize YAML asset loading in `game.load_yaml_data()` so `main.py`,
  `game/engine.py`, `game/event.py`, `game/puzzle.py`, and `game/world.py` all read from the
  shared `data/` directory through one helper instead of duplicating path and `yaml.safe_load`
  logic. Added focused helper-level coverage for the shared loader.

- Refactor — remove duplicated room-description assembly across the two UI layers. `GameEngine`
  now builds one shared room snapshot (title, body, dynamic clue text, exits, visible items,
  and time remaining), and `CursesEngine` formats that shared data for the LOCATION panel
  instead of re-deriving it independently. Added focused helper-level regression coverage for
  the shared presenter and plain-text room output.

- Refactor — remove dead wrapper functions and simplify inventory alias lookup:
  - Removed the `build_events()` pass-through in `main.py` (was a one-liner alias for
    `load_events()`); `main()` now calls `game.event.load_events()` directly. Updated the
    `GameEngine.__init__` docstring to reference `game.event.load_events` instead of the
    removed function. Removed the now-unused `EventQueue` import from `main.py`.
  - Removed the `step3_chorus_text()` wrapper in `game/puzzle.py` (was a one-liner alias for
    `state.active_clues.get("step3_song_chorus", "")`); the corresponding test in
    `test_logic_helpers.py` now reads the active-clues dict directly.
  - Simplified the inventory-item alias lookup in `handle_look` (`main.py`): replaced a 15-line
    chain of if-blocks with a module-level `_ITEM_ALIASES` dict and a 4-line lookup. All 45
    tests pass.

## 2026-05-06

- Refactor — consolidate shared direction helper logic in `game/puzzle.py`. Step 2 mirror
  rolls, Step 3 song rolls, and the step-direction correctness checks now reuse shared
  left/right helper functions instead of repeating the same direction plumbing. Focused
  puzzle/game-flow tests and the full suite pass.

- Room transition effect (curses UI): moving between rooms briefly cuts the room and log panels
  to black before the new room is drawn, giving a clean "fade to black and back" feel.
  Implemented via a `signal_transition()` hook on `GameEngine` (no-op) overridden in
  `CursesEngine` to arm a `_pending_transition` flag; `describe_current_room()` fires a 120 ms
  panel-erase pause when the flag is set. `handle_look` and startup rendering are unaffected.
  No behaviour change in the plain-text engine; all 45 tests pass.

- Code cleanup — `game/command.py`: removed the dead `ACTION_VERBS` constant (defined but never
  referenced) and eliminated the module-level YAML load that existed solely to supply the
  "unknown command" string. `CommandRegistry` now accepts an optional `unknown_message`
  constructor parameter (default matches the previous hardcoded fallback), and `main.py` passes
  the message from its already-loaded `_CMD` dict. `command.py` no longer imports `yaml` or
  `pathlib`. All 45 tests pass unchanged.

- Inventory system: player starts with five items (watch, backpack, phone, keys, wallet) stored
  in `GameState.inventory`. New `INVENTORY` / `I` command lists carried items. `DROP` is
  gracefully blocked ("You should probably hang onto that."). Examining inventory items via
  `LOOK` returns context-specific responses: backpack and phone are distractions ("You don't
  have time for that right now."), keys and wallet are irrelevant ("How will that help you find
  Room 314?"), and watch shows the time remaining. Help text updated. Nine new tests added (45
  total).

- Moved test files to `tests/` directory: added `tests/__init__.py`, updated `Makefile` test
  target to `python -m unittest discover -s tests -t .`, and updated `README.md`,
  `DEVELOPER.md`, and `ARCHITECTURE.md` to reference the new location.

- UI polish pass: the default curses interface now uses boxed LOCATION/ACTIVITY panels,
  colour-coded room/log text for commands and event notifications, a shared ASCII intro banner,
  and focused renderer tests for the new styling helpers.

- Project workflow documentation: added a root `Makefile` with `format`, `lint`, `test`, `run`,
  and `all` targets; expanded `README.md`; and added `ARCHITECTURE.md` and `DEVELOPER.md` so
  gameplay, tooling, and contributor setup are documented alongside the code.

- Comprehensive game-logic test coverage: added `test_logic_helpers.py` for parser/registry,
  state, puzzle, and event helper coverage; added `test_game_flow.py` for command handling,
  navigation, puzzle progression, and ending behavior; and expanded `test_world.py` to assert
  the shipped room graph and blocked exits.

- World-build isolation: `game/world.py` now clones cached room templates on each
  `build_world()` call instead of returning shared mutable `Room` objects, preventing exit and
  attribute mutations from leaking between world builds. Added focused regression coverage in
  `test_world.py`.

- `HELP` command: lists all available commands and their syntax; text stored in
  `data/commands.yaml` under `responses.help`; curses `_log` now splits on `\n` before wrapping
  so multi-line responses render correctly in the log panel.

- YAML extraction: all player-facing narrative strings removed from Python source files. Clue
  templates and mirror text moved to `data/puzzle.yaml`; bathroom status messages, janitor hint
  prefix, intro title/opening/teacher dialogue, end-screen text, and unknown-command response
  moved to `data/commands.yaml`. No hardcoded player-facing text remains in any `.py` file —
  all strings are referenced by unambiguous YAML keys.

- Escalating hints for bathroom puzzle: repeated `RINSE` attempts while the water is off
  (phase 1) now produce progressively more explicit guidance — first reminding the player to
  type `stop`, then explaining the sensor mechanic, and on the third+ miss spelling out the
  full RINSE → STOP → RINSE → STOP sequence. Counter resets on successful `STOP`.

- Environmental clues for puzzles: bathroom now requires `SOAP HANDS` before `RINSE HANDS` and
  blocks the exit with contextual feedback ("You feel like you should wash your hands." / "Your
  hands are still soapy.") until the puzzle is solved; janitor hallway now shows an ambient
  lyric snippet in the room description that grows from one line to the full chorus as time
  runs low, letting the player identify the song's left/right direction without issuing a
  `LISTEN` command.

- Simplification pass: precomputed `_STEP1_CLUE_TYPES` in `puzzle.py` to avoid rebuilding the
  key list on every puzzle roll; extracted `_bathroom_status()` helper in `engine.py`,
  eliminating the duplicated inline logic in `curses_engine.py` and normalising the status
  messages across both UIs; added `_route()` helper in `main.py` for the repeated 3-direction
  exit-wiring pattern; simplified flavor-chain wiring with `zip` instead of manual
  `enumerate` + conditional indexing; fixed `handle_listen` chorus display to indent each lyric
  line individually, correcting broken output for multi-line YAML block-scalar choruses.

- Code quality pass: added comprehensive docstrings to all public functions and methods across
  `game/state.py`, `game/command.py`, `game/event.py`, `game/engine.py`,
  `game/curses_engine.py`, and `main.py`, covering parameters, return values, and notable
  edge-case behaviour. Also fixed a latent bug in `CursesEngine._handle_end()` where the
  voluntary-quit branch was missing, causing the curses UI to show the "TIME'S UP" losing
  screen after a graceful `quit` (mirroring the plain-text fix from the previous session).

## 2026-05-05

- Fixed three bugs discovered during playtesting: `read` command was defined but never
  registered with the command registry; `read sign` in the lobby was rejected because the
  handler only matched the internal key `"detour_sign"` rather than the natural alias `"sign"`;
  `quit` incorrectly triggered the "TIME'S UP" losing screen instead of just printing the
  farewell message. Fix details: added `registry.register("read", handle_read)` in `main.py`;
  widened the lobby sign match to `target in ("detour_sign", "sign")`; added
  `quit: bool = False` to `GameState` and an `elif self.state.quit: pass` branch in
  `GameEngine._handle_end()` so the time-out screen is suppressed on a voluntary quit.

- Extracted janitor song pool into `data/songs.yaml` (20 entries, 10 per direction).
  `game/puzzle.py` now loads `_LEFT_SONGS` / `_RIGHT_SONGS` from YAML at import time via
  `_load_songs()`; hardcoded `list[tuple[str, str]]` literals removed.
- Extracted all command response strings into `data/commands.yaml` and all ambient/time-based
  event definitions into `data/events.yaml`. `main.py` now loads a `_CMD` dict from
  `commands.yaml` at module level and delegates `build_events()` to `load_events()` in
  `game/event.py`. Added `_build_condition()` to `game/event.py` to translate declarative YAML
  condition specs (`time_range`, `move_count_eq`, `move_count_gte`, `location`,
  `wrong_turns_gte`, `all`) into `EventCondition` callables. 15 events, all command verbs
  covered. Hardcoded strings removed from Python source.
- Extracted all room description/name/exit/item/attribute data into `data/rooms.yaml`.
  `game/world.py` now loads and parses the YAML at import time via `pyyaml`; `build_world()`
  and `FLAVOR_ROOM_POOL` are derived from that data. Added `requirements.txt` tracking
  `pyyaml>=6.0`. Room count: 15 (9 structural + 6 flavor).
- Added curses-based split-pane UI (`game/curses_engine.py`, `CursesEngine`). Layout: 1-line
  header (title + live time); room panel (upper ~40% — name, description, exits, items, puzzle
  hints); scrolling log panel (event messages and command output); 1-line command input. Colour
  support when the terminal provides it. `main.py` updated with `--no-curses` flag to fall back
  to plain-text mode; curses is the default.
- Added win/lose/weird endings: entering `room_314` sets `state.won = True` and
  `state.game_over = True` (`main.py`); `engine._handle_end()` now has three branches — weird
  ending (won with ≥300 s remaining: empty room, exam is tomorrow), normal win, and time-out
  lose. Lose condition was already implicit in `GameState.tick()`.
- Added ambient narrative events (10 new one-shot events in `build_events()`, `main.py`):
  location-based (lobby ceiling tiles, hallway no signal, intersection door numbers after a
  wrong turn, bathroom stall click, janitor mopping the same spot); move-count tension
  escalation (door closes at move 3, footsteps stop at 8, light buzzes at 13, marker smell at
  20); additional 3-minute time warning (165–180 s remaining).- Implemented wrong-way reset: on
  an incorrect direction at `intersection_4way`, the player is routed through a
  randomly-sampled chain of 2–3 flavor rooms (from `FLAVOR_ROOM_POOL`) before looping back to
  the 4-way intersection; Step 1 clue is re-rolled on every re-entry (`step1_roll` was already
  called on entry), giving a genuinely fresh puzzle each time the player is lost. Added
  `import random` and `FLAVOR_ROOM_POOL` import to `main.py`.

## 2026-05-04

- Implemented puzzle Step 3/4 – janitor song clue: `step3_is_correct` helper added to
  `game/puzzle.py`; `hallway_janitor` gains left/right/forward exits (puzzle-gated); exits
  wired on entry — correct direction (from song) leads to `hallway_final`, wrong directions
  bounce through `flavor_copy_room` (whose `forward` exit is redirected to `hallway_janitor` so
  wrong-way bounces loop back without re-rolling the clue); `LISTEN` in janitor hallway returns
  the song chorus and sets `step3_song_heard` flag.
- Redesigned handwashing puzzle as 4-phase motion-sensor trick: phase 0–4 state machine in
  `room.attributes["wash_phase"]`; `RINSE HANDS` and `STOP` commands advance phases; trick is
  RINSE → STOP (resets sensor) → RINSE quickly (water stays running) → STOP (done); engine
  shows phase-appropriate sink hint; `examine sink` shows context-sensitive status.

- Configured Prettier for Markdown autoformat on save: `.prettierrc` (printWidth 95, proseWrap
  always), `.prettierignore` (excludes node_modules, pycache, venv, etc.),
  `.vscode/settings.json` (format-on-save for `[markdown]`). Applied formatting to all existing
  `.md` files.
- Added Python game framework: `game/` package with `Room`,
  `Command`/`CommandParser`/`CommandRegistry`, `Event`/`EventQueue`, `GameState`, and
  `GameEngine` classes.
- Added `main.py` entry point with stub room map, full command set (movement, look, examine,
  read, open, knock, listen, check, help, quit), and ambient narrative events.
- Built out full room map in `game/world.py`: lobby, approach hallway, 4-way intersection,
  3-way intersection (two variants — entrance and post-bathroom exit), bathroom (with
  sink/mirror puzzle attributes), janitor's hallway, final stretch, Room 314, and a pool of 6
  flavor rooms (`FLAVOR_ROOM_POOL`). Puzzle-directed exits are `None` placeholders; routing
  logic will wire them when puzzle steps are implemented.
- Run with: `python main.py`
