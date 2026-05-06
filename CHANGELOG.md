## 2026-05-05

- Extracted all room description/name/exit/item/attribute data into `data/rooms.yaml`.
  `game/world.py` now loads and parses the YAML at import time via `pyyaml`; `build_world()`
  and `FLAVOUR_ROOM_POOL` are derived from that data. Added `requirements.txt` tracking
  `pyyaml>=6.0`. Room count: 15 (9 structural + 6 flavour).
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
  randomly-sampled chain of 2–3 flavour rooms (from `FLAVOUR_ROOM_POOL`) before looping back to
  the 4-way intersection; Step 1 clue is re-rolled on every re-entry (`step1_roll` was already
  called on entry), giving a genuinely fresh puzzle each time the player is lost. Added
  `import random` and `FLAVOUR_ROOM_POOL` import to `main.py`.

## 2026-05-04

- Implemented puzzle Step 3/4 – janitor song clue: `step3_is_correct` helper added to
  `game/puzzle.py`; `hallway_janitor` gains left/right/forward exits (puzzle-gated); exits
  wired on entry — correct direction (from song) leads to `hallway_final`, wrong directions
  bounce through `flavour_copy_room` (whose `forward` exit is redirected to `hallway_janitor`
  so wrong-way bounces loop back without re-rolling the clue); `LISTEN` in janitor hallway
  returns the song chorus and sets `step3_song_heard` flag.
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
  flavour rooms (`FLAVOUR_ROOM_POOL`). Puzzle-directed exits are `None` placeholders; routing
  logic will wire them when puzzle steps are implemented.
- Run with: `python main.py`
