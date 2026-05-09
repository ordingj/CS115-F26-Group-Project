# Developer Guide

## Setup

Requirements: **Python 3.12 or later** and Node.js.

1. Create and activate a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
```

1. Install runtime dependencies.

```bash
python -m pip install -r requirements.txt
```

1. Install developer tooling.

```bash
python -m pip install ruff
npm install
```

`ruff` powers the Python format/lint targets. Prettier is installed from `package.json` for
Markdown and data-file formatting.

## Daily workflow

```bash
make format
make lint
make test
make coverage
make run
make all
```

- `make format`: runs `ruff format` and Prettier.
- `make lint`: runs `ruff check`.
- `make test`: runs the full `unittest` suite.
- `make coverage`: reruns the test suite under `coverage.py`, prints a source-file report for
  `main.py` and `game/*.py`, and fails if any of those runtime modules is below 80% statement
  coverage.
- `make run`: launches the game with the default curses UI.
- `make all`: runs format, lint, and test in sequence.

For terminals that do not support curses, run:

```bash
python main.py --no-curses
```

## Codebase conventions

- Keep player-facing narrative text in `data/*.yaml`, not hardcoded in Python.
- Prefer small, deterministic helpers in `game/` and keep orchestration in `main.py`.
- Add or update unit tests whenever command handling, puzzle state, routing, or endings change.
- Update `TODO.md`, `CHANGELOG.md`, `README.md`, and `ARCHITECTURE.md` when completing a task.

## Testing guidance

- Use `tests/test_core_helpers.py` for parser/state/loader behavior.
- Use `tests/test_puzzle_helpers.py` for bathroom, janitor, and puzzle helper behavior.
- Use `tests/test_ui_event_helpers.py` for renderer and event-helper behavior.
- Use `tests/test_command_flow.py` for supported commands and inventory command-flow coverage.
- Use `tests/test_puzzle_flow.py` for end-to-end routing and puzzle progression behavior.
- Use `tests/test_endings.py` for end-state output checks.
- Use `tests/test_world.py` for world-construction and room-map regressions.

Prefer targeted test runs while iterating. Finish with `make all` when only existing files are
changing, or `make all coverage` when new source/test files were added and you need the
coverage gate as part of the final pass.
