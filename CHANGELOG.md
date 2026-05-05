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
