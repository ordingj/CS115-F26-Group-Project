# Test Guide

This document is the detailed reference for the repository's automated test strategy. Use it
alongside `make test`, `make coverage`, `README.md`, and `DEVELOPER.md` when validating a
change.

## Goals

- Keep day-to-day iteration fast with focused `unittest` runs.
- Protect game logic, routing, endings, and curses behavior with stable regression coverage.
- Enforce an 80% per-file statement-coverage floor for shipped runtime modules.

## Standard Commands

```bash
make test
make coverage
make all
python -m unittest discover -s tests -t .
python -m unittest tests.test_curses_helpers
python -m unittest tests.test_curses_helpers.CursesEngineMethodTest.test_get_input_reads_prompt_and_restores_terminal_modes
```

- `make test`: runs the full `unittest` suite under `tests/`.
- `make coverage`: reruns the full suite under `coverage.py`, prints a report for the runtime
  modules, and then enforces the per-file threshold with `tests/check_coverage_threshold.py`.
- `make all`: runs formatting, linting, and the full test suite in sequence.
- `python -m unittest discover -s tests -t .`: direct equivalent of `make test`.
- `python -m unittest tests.test_curses_helpers`: example focused module run while iterating.
- `python -m unittest tests.test_curses_helpers.CursesEngineMethodTest.test_get_input_reads_prompt_and_restores_terminal_modes`:
  example of targeting one specific regression test.

Prefer focused test commands while developing, then finish with `make all` for existing-file
changes or `make all coverage` when new source or test files are added.

## Suite Map

| File                           | Coverage area                                                                  | Use it when...                                                                   |
| ------------------------------ | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| `tests/helpers.py`             | Shared engine builders, room fixtures, and dispatch helpers                    | A new test needs the standard world/state/registry wiring                        |
| `tests/test_core_helpers.py`   | Parser, registry, state, YAML loading, and composition-root helpers            | You change state bookkeeping, command parsing, loaders, or `game/main.py` wiring |
| `tests/test_puzzle_helpers.py` | Step-specific bathroom, janitor, and puzzle helpers                            | You change clue generation, bathroom state transitions, or song logic            |
| `tests/test_engine_helpers.py` | Plain-text engine formatting and loop helpers                                  | You change shared engine output or plain-mode flow                               |
| `tests/test_curses_helpers.py` | Curses rendering, prompt/input handling, timer updates, and end-screen helpers | You touch `CursesEngine` or `curses_rendering.py`                                |
| `tests/test_event_helpers.py`  | Event-condition loading and queue behavior                                     | You change declarative event specs or queue evaluation                           |
| `tests/test_command_flow.py`   | Supported commands and inventory command behavior                              | You change player verbs, fallbacks, or command responses                         |
| `tests/test_puzzle_flow.py`    | Navigation and end-to-end puzzle progression                                   | You change room routing, blockers, wrong-turn handling, or the win path          |
| `tests/test_endings.py`        | Win, weird ending, loss, and quit output selection                             | You change ending text or end-state branching                                    |
| `tests/test_world.py`          | World construction, cloning, and base room graph expectations                  | You change `data/rooms.yaml` or world-building code                              |

## Testing Strategy

The suite is intentionally split across two layers:

1. Focused helper tests validate deterministic logic in isolation.
2. Flow tests verify that rooms, commands, events, and endings still work together.

Use the smallest owning suite first. For example:

- State, parser, or registry changes: start with `tests/test_core_helpers.py`.
- Bathroom, janitor, or clue helpers: start with `tests/test_puzzle_helpers.py`.
- Curses redraw, prompt, or timer changes: start with `tests/test_curses_helpers.py`.
- Room transitions or wrong-turn routing: add `tests/test_puzzle_flow.py` coverage.
- Ending text or replay/quit behavior: validate `tests/test_endings.py` and, for curses,
  `tests/test_curses_helpers.py`.

This keeps unit coverage precise without relying only on broad integration tests.

## Coverage Workflow

`make coverage` runs the same full suite as `make test`, but wraps it in `coverage.py` and then
enforces a threshold.

The Makefile executes these steps:

```bash
python -m coverage erase
python -m coverage run -m unittest discover -s tests -t .
python -m coverage report --include='game/main.py,game/*.py,game/commands/*.py,game/engine/*.py,game/puzzles/*.py'
python tests/check_coverage_threshold.py --threshold 80 game/main.py game/*.py game/commands/*.py game/engine/*.py game/puzzles/*.py
```

Important details:

- The threshold is per file, not a single project-wide average.
- The enforced files are the shipped runtime modules under `game/` plus `game/main.py`.
- Test files and documentation files are not part of the coverage gate.
- Files with no executable statements count as 100% inside the threshold script.

## Interpreting Results

### `unittest` failures

Typical outputs include `FAILED (failures=...)` or `FAILED (errors=...)`.

- A failure usually means an assertion no longer matches the intended behavior.
- An error usually means an exception, import problem, or broken setup path.
- Re-run the first failing module or test directly before widening scope.

### Coverage failures

If the threshold step fails, the output looks like this:

```text
Coverage threshold failures (<80.0%):
	game/engine/curses_engine.py: 74.3%
```

That means the suite may still be green overall, but one runtime file needs more direct test
coverage. Add or expand tests that execute the changed branch paths in that file, then rerun
`make coverage`.

### Green focused tests but red full-suite results

This usually means one of these happened:

- A shared helper changed behavior that another suite also depends on.
- A flow suite still reflects the old routing or output contract.
- A coverage-only path was missed because the focused run did not touch all affected files.

When that happens, keep the focused regression test, then widen to the smallest additional
suite that exercises the changed ownership boundary.

## Notes for Curses Work

- The curses helper suite uses fake window objects and patching instead of relying on a live
  terminal.
- Prefer `tests/test_curses_helpers.py` for panel rendering, prompt behavior, timer polling,
  and replay/end-screen regressions.
- Use flow tests only after the curses helper surface is stable enough to prove the end-to-end
  move path.
