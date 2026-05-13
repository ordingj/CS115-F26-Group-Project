# CS115 S26 Final Project - **Final Exam: Room 314**

Contributors: Joseph Ording, ChatGPT 5.4, Claude Sonnet 4.6

## Game Overview

Final Exam: Room 314 is a timed text adventure about finding the right classroom before the
exam starts. Every command costs time, the hallway layout changes around you, and the correct
route has to be inferred from environmental clues instead of a static map.

The default experience uses a curses split-pane interface with a room panel, scrolling event
log, live time display, color-coded command/event/output styling, and a small ASCII intro
banner. A plain-text fallback is also available for terminals that do not support curses.

## How to run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m game.main
```

Run the plain-text fallback instead of the curses UI:

```bash
python -m game.main --no-curses
```

## Requirements

- Python 3.12 or later
- Python packages listed in `requirements.txt`
- Node.js dependencies from `package.json` for documentation formatting

## Common development commands

```bash
make format
make lint
make test
make coverage
make run
make all
```

`make all` runs formatting, linting, and the full unit-test suite in sequence. `make coverage`
reruns the unit-test suite under coverage reporting and fails if any runtime module in
`game/main.py`, `game/*.py`, `game/commands/*.py`, `game/engine/*.py`, or `game/puzzles/*.py`
falls below 80% statement coverage.

## Gameplay summary

- Goal: reach Room 314 before the ten-minute timer expires.
- In curses mode the header now counts down live while you wait at the prompt.
- Commands still cost 15 seconds, so the timer both ticks in real time and drops on actions.
- The curses timer turns yellow below five minutes remaining and red below one minute.
- Step 1: solve the four-way intersection clue to reach the restroom junction.
- Step 2: complete the handwashing puzzle to reveal the mirror clue.
- Step 3: use the mirror clue to find the janitor hallway.
- Step 4: listen to the janitor's song clue to choose the final direction.
- Wrong turns send the player through flavor rooms and eventually back into the puzzle loop.
- Reaching Room 314 with at least five minutes remaining triggers the weird ending.

## Testing

```bash
make test
make coverage
```

The automated tests cover command parsing and dispatch, room navigation and blocked exits,
puzzle progression, YAML-driven event triggers, world-building integrity, and the win/lose/quit
end states. When a large diff introduces new source or test files, prefer `make all coverage`
for the final verification pass so lint, tests, and the per-file coverage threshold run
together. See `tests/TESTS.md` for the suite-by-suite map, focused `unittest` commands, and
coverage-failure interpretation guide.

## Project structure

```text
game/
  __init__.py        # Shared package helpers for loading YAML assets from data/
  main.py            # Composition root; builds rooms, commands, events, and starts the engine
  commands/
    basic_commands.py   # Simple stateless and inventory command registrations
    command.py          # Command, parser, registry, and shared handler adapters
    player_commands.py  # Command assembly plus non-movement room-target handlers
    player_movement.py  # Movement verbs plus puzzle routing and room-entry side effects
  engine/
    engine.py           # Plain-text game loop and shared room-presentation helpers
    curses_engine.py    # Split-pane curses UI with boxed panels and color-coded log styling
    curses_rendering.py # Shared panel, wrapping, and style helpers for the curses UI
  puzzles/
    bathroom.py         # Step 2 state, clue-roll, and bathroom action helpers
    bathroom_view.py    # Read-only bathroom clue and room-target helpers
    intersection.py     # Step 1 four-way clue roll and clue text helpers
    janitor.py          # Step 3 song-roll, formatting, and janitor command helpers
    puzzle.py           # Shared clue-storage and direction-matching helpers
  room.py            # Room dataclass (exits, items, attributes)
  event.py           # Event, EventQueue (time/state-triggered narrative beats)
  state.py           # GameState (time, location, puzzle step, flags)
  world.py           # YAML-backed room loading and world construction
data/
  rooms.yaml         # Room graph and room metadata
  commands.yaml      # Player-facing command responses and UI strings
  events.yaml        # Ambient narrative event definitions
  puzzle.yaml        # Puzzle clue templates
  songs.yaml         # Janitor song pools for left/right clues
tests/
  helpers.py             # Shared engine builders plus flow-test dispatch helpers
  test_core_helpers.py   # Command, state, and shared YAML-loader helper tests
  test_puzzle_helpers.py # Bathroom, janitor, and puzzle helper tests
  test_engine_helpers.py  # Plain-engine formatting and engine-loop helper tests
  test_curses_helpers.py  # Curses renderer and curses-engine helper tests
  test_event_helpers.py   # Event-condition and EventQueue helper tests
  test_command_flow.py   # Supported commands and inventory command-flow coverage
  test_puzzle_flow.py    # Navigation and puzzle progression integration tests
  test_endings.py        # Win, loss, weird ending, and quit output coverage
  test_world.py          # World-build regression tests and room-map assertions
Makefile               # Format, lint, test, and run targets
SLIDES.md              # Presentation scaffold for summary, architecture, workflow, and testing
STORY.md               # Narrative design notes and early puzzle planning
```

## Commands

- Movement: `forward` or `f`, `back` or `b`, `left` or `l`, `right` or `r`
- Observation: `look [item]`, `examine [item]`, `read [item]`, `listen`, `check watch`
- Interaction: `open [item]`, `knock [item]`, `soap hands`, `rinse hands`, `wash hands`,
  `dry hands`, `stop`
- Utility: `help`, `quit`, `exit`
