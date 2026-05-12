<!-- working-on: Identify opportunities across the codebase to simplify, refactor, or remove redundant and overlapping functions in ways that reduce complexity and improve maintainability. -->

# Project Tasklist

- [x] tests/TESTS.md - document test strategy, coverage, and instructions for running tests and
      interpreting results - [x] Added `tests/TESTS.md` as the canonical testing reference,
      including the suite map, focused `unittest` commands, the `make coverage` workflow, and
      guidance for interpreting failures.

- [x] implement the live curses countdown in the header, including warning colors for low time
  - [x] Added a live monotonic countdown for the curses session, kept the existing 15-second
        action penalty, and switched the timer color to yellow below 5:00 and red below 1:00.
        Focused core-helper and curses-helper tests cover the deadline sync, idle input
        polling, and threshold colors.

- [x] verify the `hallway_final -> room_314` transition shows the ending instead of a blank
      screen in both the plain-text and curses engines
  - [x] Hardened the shared curses renderer to clip by terminal cell width instead of raw
        character count, preventing the `room_314` end screen from silently dropping its text
        on narrower terminals when wide punctuation is present. Added focused curses regression
        coverage for the narrow-width render path.

- [x] create data/DATA.md - catalog the yaml files; detailed descriptions of
      structure/fields/entries, etc with examples; list all possible values when feasible, or
      point to source (i.e. list of commands, etc.)

- [x] add numpy-style docstrings to all functions and methods; add module-level docstrings
      where appropriate; add copious inline comments explaining complex logic and design
      decisions throughout the codebase; include tests, public/private functions, etc.; this
      should be very thorough and consistent across the codebase to ensure it's easy to
      understand and maintain for future developers; this is a major part of the grading, so we
      need to do a great job here

- [x] documentation updates:
  - [x] there should be no narrative text or user-facing strings hardcoded in the Python; all
        such text should be loaded from YAML files at runtime, with clear keys and structure to
        make it easy to understand and edit the narrative content without touching the code
  - [x] yaml files should be well-organised and clearly structured, with comments explaining
        the purpose of each section and any non-obvious entries; use consistent formatting and
        naming conventions to make it easy to understand and edit the data

- [/] Identify opportunities across the codebase to simplify, refactor, or remove redundant and
  overlapping functions in ways that reduce complexity and improve maintainability. Include
  tests, CSS, and dev tools/scripts. Update callsites to use the simplified flow, then remove
  the old code and any related tests without preserving fallbacks, shims, aliases, or wrappers
  for removed or consolidated functions. Small refactors have largely been exhausted and
  remaining ones are likely constrained by complexity boundaries, so prioritize larger
  refactors with maximum impact, especially those spanning multiple files or modules. Split
  modules over 500 lines (excluding docstrings/comments). Be deliberate about complexity when
  deciding whether to inline small helpers, combine related helpers, or split large ones.
  Maintain the default complexity caps enforced by linters; do not raise limits, add ignores,
  or otherwise bypass those constraints to make a refactor fit. Ensure refactors are thoroughly
  tested and that the test suite remains comprehensive and robust throughout. Update
  documentation to reflect the new code structure and any resulting changes in functionality or
  usage. Treat this as a major, multi-pass effort requiring careful attention to detail to
  produce a clean, modern codebase without legacy artifacts.
  - [/] Code quality audit — ensure there are no legacy, compatibility, migration, or fallback
    shims or surfaces left in the codebase, and that everything is aligned directly with the
    current implementation. Update stale references to their proper locations and clean up
    deprecated code. If any legacy or compatibility code cannot be removed immediately, clearly
    mark it and document the removal plan. Update documentation to remove references to legacy
    or compatibility code and accurately reflect the current state of the implementation.
    Update tests that still rely on legacy or compatibility paths to use the modern
    implementation, and remove tests that are no longer relevant once old code is deleted. Keep
    existing linter complexity caps in place during this work; do not loosen thresholds or rely
    on ignores as a substitute for simplifying the code. Make this audit thorough and
    systematic across code, documentation, and tests so there are no lingering references to
    legacy or compatibility code anywhere in the project.
  - [/] Focus on redundant and overlapping functions across the codebase, especially in areas
    that have grown organically without enough refactoring. Consolidate where doing so
    meaningfully reduces complexity and improves maintainability. Update callsites to the
    simplified flows and remove the replaced code and related tests without keeping fallbacks
    or shims. Do not avoid large refactors just because they span multiple modules; those are
    often the highest-value opportunities and should be approached methodically with a strong
    emphasis on quality and maintainability. Consider complexity tradeoffs when choosing
    whether to inline small helpers, combine related helpers, or split large ones. Keep default
    linter complexity limits unchanged throughout; no cheesing by increasing caps, suppressing
    rules, or adding ignores instead of improving the design. Keep testing rigorous,
    documentation current, and the overall effort deliberate. This is long-term work that may
    require multiple passes, and it should be done carefully rather than rushed so each
    refactor is successful and does not introduce new issues.

- [x] implement inventory system (start with default items: watch, backpack, phone, keys,
      wallet); allow player to look at the items in their inventory; if they try to drop
      something, say "You should probably hang onto that." if they try to look in their
      backpack, or mess with their phone, say "You don't have time for that right now." if they
      try to use their keys or wallet, say "How will that help you find Room 314?"

- [x] add a transition effect when moving between rooms - fade to black and back

- [x] tests moved to tests/ folder - make any necessary updates to codebase/documentation

- [x] write tests for all game logic; this will be a major part of the grading, so we need to
      do a great job here
  - [x] test command parsing and handling; ensure all commands are recognised and produce the
        expected output; test edge cases and invalid input
  - [x] test room navigation; ensure moving in each direction from each room leads to the
        correct destination; test that blocked paths are handled correctly
  - [x] test puzzle mechanics; ensure each puzzle step behaves as expected based on player
        actions and state; test that clues are provided correctly and that the puzzle resets
        properly on failure
  - [x] test event triggering; ensure events trigger at the correct times and locations based
        on the game state
  - [x] test win/lose conditions; ensure the game ends correctly when the player wins or loses,
        and that the correct ending is shown based on the remaining time

- [x] create Makefile targets for formatting (format), linting (lint), testing (test), running
      the game (run); create 'all' target that runs formatting, linting, testing in sequence

- [x] extract all narrative text into yaml files and load them in at runtime to clean up the
      code; also makes it easier to add new rooms/events/commands without touching code
  - [x] do the same for commands and events; don't hardcode any strings in the python,
        reference the yaml data instead; use unambiguous keys to look up the right string for
        each situation, so it's obvious when editing the yaml what each string is for and you
        don't have to cross-reference with the code to understand the context

- [x] implement environmental clues for puzzles
  - [x] bathroom "You feel like you should wash your hands." if they try to leave without
        washing; "You should use soap." if they rinse without soap; "Your hands are still
        soapy." if they don't rinse long enough. "Your hands are clean. You notice something on
        the wall behind you in the mirror." if they do it right.
  - [x] janitor "The janitor is humming a song. You can't quite remember the title, but the
        lyrics go something like..." (then show part of the chorus); show more of the lyrics as
        the time gets lower; there is no interaction with the janitor, just the clue in the
        lyrics; the player has to identify the song and then choose the correct direction based
        on whether it's a left or right clue.

- [x] implement 'help' command that lists available commands and their syntax

- [x] extract song titles/lyrics to yaml (`data/songs.yaml`); load in `game/puzzle.py`

- [x] framework:
  - [x] define asset types: rooms, commands, events (`game/room.py`, `game/command.py`,
        `game/event.py`)
  - [x] define commands: movement, actions, etc. (`game/main.py` – `build_commands`)
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
