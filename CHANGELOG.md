## 2026-05-06

- YAML extraction: all player-facing narrative strings removed from Python source files.
  Clue templates and mirror text moved to `data/puzzle.yaml`; bathroom status messages,
  janitor hint prefix, intro title/opening/teacher dialogue, end-screen text, and
  unknown-command response moved to `data/commands.yaml`. No hardcoded player-facing text
  remains in any `.py` file — all strings are referenced by unambiguous YAML keys.

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
