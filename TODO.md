# Project Tasklist

- [x] code quality pass - add type annotations, docstrings, comments; refactor for clarity and
  maintainability; this will be judged so we need to do a great job here

- [x] extract song titles/lyrics to yaml (`data/songs.yaml`); load in `game/puzzle.py`

- [x] extract all description text into yaml files and build rooms from those to clean up the
      code; also makes it easier to add new rooms without touching code
  - [x] do the same for commands and events

- [x] Create framework for text adventure game
  - [x] define asset types: rooms, commands, events (`game/room.py`, `game/command.py`,
        `game/event.py`)
  - [x] define commands: movement, actions, etc. (`main.py` – `build_commands`)
  - [x] define states: time, location, puzzle states (`game/state.py`)

- [x] Build out full room map (lobby → hallways → bathroom → Room 314)
  - [x] lobby - starting point, two hallways (one blocked, one leads to 4-way intersection);
        can never return to lobby after leaving.
  - [x] 4-way intersection - puzzle node; exits set dynamically by puzzle Step 1
  - [x] 3-way intersection - bathroom door forward; other three directions are hallways;
        `intersection_3way_exit` models the reversed-orientation version after bathroom exit
    - [x] bathroom defined with sink/mirror puzzle attributes (Step 2)
  - [x] hallway with janitor - janitor present; song clue tracked in state (Step 4)
  - [x] Room 314 - win condition room defined
  - [x] flavor hallway pool - 6 atmospheric rooms (`game/world.py::FLAVOR_ROOM_POOL`); routing
        logic will splice 1-3 between puzzle nodes at runtime

- [x] Implement puzzle Step 1 – 4-way intersection clue system (randomised each cycle)
- [x] Implement puzzle Step 2 – bathroom sink/mirror clue
  - [x] puzzle mechanics - rinse hands/stop rinsing and timing
- [x] Implement puzzle Step 3/4 – janitor song clue
  - [x] create two song lists for left/right clues with lyrics; randomly select one set
        (song/lyrics) for each encounter
- [x] Implement "wrong way" reset - if player goes wrong way, give them a few random rooms and
      then return them to the 4-way with new clue; reset the puzzle states/randomise the clues
- [x] events - add ambient narrative events that trigger based on time/location/state to add
      tension and foreshadowing (e.g. footsteps, whispers, flickering lights, etc.)
- [x] Add win condition – enter Room 314 before time runs out
- [x] Add lose condition – time runs out before entering Room 314
- [x] Add weird ending – arrive in Room 314 with at least 5 minutes remaining

- [x] implement curses-based UI with live-updating room descriptions, command input, and event
      notifications
  - [x] upper section for room description, lower section with command input and event log
