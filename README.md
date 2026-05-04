# CS115 S26 Group Project

## **Final Exam: Room 314**

Group Members: Joseph Ording, Raj, Jerry, Matthew

## How to run

```bash
python main.py
```

## Project structure

```
main.py          # Entry point; builds rooms, commands, events, and starts the engine
game/
  room.py        # Room dataclass (exits, items, attributes)
  command.py     # Command, CommandParser, CommandRegistry
  event.py       # Event, EventQueue (time/state-triggered narrative beats)
  state.py       # GameState (time, location, puzzle step, flags)
  engine.py      # GameEngine – main loop and room rendering
STORY.md         # Full narrative design and puzzle walkthrough
```

## Commands

`forward` · `back` · `left` · `right` · `look` · `examine` · `read <item>` · `open <item>` ·
`knock <item>` · `listen` · `check watch` · `help` · `quit`
