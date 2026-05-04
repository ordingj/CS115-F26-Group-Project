## 2026-05-04

- Implemented puzzle Step 1 – 4-way intersection clue system (`game/puzzle.py`):
  three randomised clue types (flickering light, bake-sale sign, shadow); correct
  direction stored in `state.active_clues["step1_correct_dir"]`; clue text injected
  into room description by `GameEngine`; wrong-way moves bounce through a flavour room
  and re-roll a fresh clue on return. Also stubbed Step 2 (`step2_roll`/`step2_mirror_text`)
  and Step 3/4 (`step3_roll`/`step3_chorus_text`, with 10-song left/right pools) in
  `game/puzzle.py` for upcoming tasks.
- Implemented puzzle Step 2 – bathroom sink/mirror clue: `wash`/`use` command triggers
  sink interaction (water off → soap → rinse); `examine mirror` / `read mirror` reveal
  backwards clue (GO LEFT or GO RIGHT, randomised per game); mirror only readable after
  washing hands. `examine sink` shows sink status. Engine shows sink-running hint on room
  entry. Bathroom exit wires 3-way exits from mirror direction.

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
