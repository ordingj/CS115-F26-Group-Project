## 2026-05-04

- Configured Prettier for Markdown autoformat on save: `.prettierrc` (printWidth 95,
  proseWrap always), `.prettierignore` (excludes node_modules, pycache, venv, etc.),
  `.vscode/settings.json` (format-on-save for `[markdown]`). Applied formatting to all
  existing `.md` files.
- Added Python game framework: `game/` package with `Room`,
  `Command`/`CommandParser`/`CommandRegistry`, `Event`/`EventQueue`, `GameState`, and
  `GameEngine` classes.
- Added `main.py` entry point with stub room map (lobby, main hallway, 4-way intersection),
  full command set (movement, look, examine, read, open, knock, listen, check, help, quit), and
  ambient narrative events.
- Run with: `python main.py`
