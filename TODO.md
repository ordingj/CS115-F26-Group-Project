# Project Tasklist

- [x] Configure Prettier for Markdown autoformat on save
- [x] Create framework for text adventure game
  - [x] define asset types: rooms, commands, events (`game/room.py`, `game/command.py`,
        `game/event.py`)
  - [x] define commands: movement, actions, etc. (`main.py` – `build_commands`)
  - [x] define states: time, location, puzzle states (`game/state.py`)
- [ ] Build out full room map (lobby → hallways → bathroom → Room 314)
  - [ ] lobby - starting point, two hallways (one blocked, one leads to 4-way intersection);
        contains random clue for Step 1; can never return to lobby after leaving.
  - [ ] 4-way intersection - resets puzzle sequence, gives clue for Step 2
  - [ ] 3-way intersection - bathroom door on one wall (forward), other three directions are
        hallways (back, left, right); when player exits from bathroom, they return to this
        intersection with the directions reversed (door behind)
    - [ ] contains puzzle for Step 2 (sink/mirror clue)
  - [ ] hallway with janitor - janitor humming a tune that gives clue for Step 3
  - [ ] Room 314 - win condition
  - [ ] hallways - random rooms with weird signs/noises/etc. to add flavour and make wrong way
        more disorienting; insert a random number of these (1-3) between each puzzle step

- [ ] Implement puzzle Step 1 – 4-way intersection clue system (randomised each cycle)
- [ ] Implement puzzle Step 2 – bathroom sink/mirror clue
  - [ ] puzzle mechanics - rinse hands/stop rinsing and timing
- [ ] Implement puzzle Step 3/4 – janitor song clue
  - [ ] create two song lists for left/right clues with lyrics; randomly select one set
        (song/lyrics) for each encounter
- [ ] Implement "wrong way" reset - if player goes wrong way, give them a few random rooms and
      then return them to the 4-way with new clue; reset the puzzle states/randomise the clues
- [ ] events - add ambient narrative events that trigger based on time/location/state to add
      tension and foreshadowing (e.g. footsteps, whispers, flickering lights, etc.)
- [ ] Add win condition – enter Room 314 before time runs out
- [ ] Add lose condition – time runs out before entering Room 314
- [ ] Add weird ending – arrive in Room 314 with at least 5 minutes remaining
