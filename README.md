# CS115 S26 Group Project - **Final Exam: Room 314**

Group Members: Joseph Ording, Raj, Jerry, Matthew

## Game overview

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
python main.py
```

Run the plain-text fallback instead of the curses UI:

```bash
python main.py --no-curses
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
`main.py` or `game/*.py` falls below 80% statement coverage.

## Gameplay summary

- Goal: reach Room 314 before the ten-minute timer expires.
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
together.

## Project structure

```text
main.py              # Entry point; builds rooms, commands, events, and starts the engine
game/
  __init__.py        # Shared package helpers for loading YAML assets from data/
  basic_commands.py  # Simple stateless and inventory command registrations
  bathroom.py        # Shared bathroom puzzle helpers used by the command layer
  janitor.py         # Shared janitor song-clue formatting helpers
  player_commands.py # Command assembly plus non-movement room-target and interaction handlers
  player_movement.py # Movement verbs, puzzle routing, and room-entry side effects
  movement_routing.py # Dynamic room-entry routing and clue-driven exit wiring helpers
  movement_validation.py # Shared movement rule tables and wrong-way validation helpers
  curses_rendering.py # Shared panel, wrapping, and style helpers for the curses UI
  room.py            # Room dataclass (exits, items, attributes)
  command.py         # Command, parser, registry, and shared command-handler adapters
  event.py           # Event, EventQueue (time/state-triggered narrative beats)
  state.py           # GameState (time, location, puzzle step, flags)
  puzzle.py          # Randomized clue generation and puzzle helpers
  world.py           # YAML-backed room loading and world construction
  engine.py          # Plain-text game loop and shared room-presentation helpers
  curses_engine.py   # Split-pane curses UI with boxed panels and color-coded log styling
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
  test_ui_event_helpers.py # Engine formatting and event helper tests
  test_command_flow.py   # Supported commands and inventory command-flow coverage
  test_puzzle_flow.py    # Navigation and puzzle progression integration tests
  test_endings.py        # Win, loss, weird ending, and quit output coverage
  test_world.py          # World-build regression tests and room-map assertions
Makefile               # Format, lint, test, and run targets
STORY.md               # Narrative design notes and early puzzle planning
```

## Commands

- Movement: `forward`, `back`, `left`, `right`
- Observation: `look [item]`, `examine [item]`, `read [item]`, `listen`, `check watch`
- Interaction: `open [item]`, `knock [item]`, `soap hands`, `rinse hands`, `wash hands`, `stop`
- Utility: `help`, `quit`
