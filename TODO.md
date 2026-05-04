# Project Tasklist

- [x] Create framework for text adventure game
  - [x] define asset types: rooms, commands, events (`game/room.py`, `game/command.py`, `game/event.py`)
  - [x] define commands: movement, actions, etc. (`main.py` – `build_commands`)
  - [x] define states: time, location, puzzle states (`game/state.py`)
- [ ] Build out full room map (lobby → hallways → bathroom → Room 314)
- [ ] Implement puzzle Step 1 – 4-way intersection clue system (randomised each cycle)
- [ ] Implement puzzle Step 2 – bathroom sink/mirror clue
- [ ] Implement puzzle Step 3/4 – hallway shift + janitor song clue
- [ ] Implement "wrong way" reset and ominous flavour escalation
- [ ] Add win condition – enter Room 314 before time runs out
