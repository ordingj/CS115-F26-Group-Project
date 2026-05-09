# Data Directory — YAML Catalog

This document describes every YAML file in `data/`. Each file is loaded at runtime by
`game.load_yaml_data()` (see `game/__init__.py`). Python source files **never** contain
hardcoded narrative strings; all user-facing text lives here.

---

## Table of Contents

1. [commands.yaml](#commandsyaml)
2. [rooms.yaml](#roomsyaml)
3. [events.yaml](#eventsyaml)
4. [puzzle.yaml](#puzzleyaml)
5. [songs.yaml](#songsyaml)

---

## commands.yaml

**Loaded by:** `game/basic_commands.py`, `game/bathroom.py`, `game/janitor.py`,
`game/player_commands.py`, `game/player_movement.py`, `game/engine.py`,
`game/curses_engine.py`, `game/curses_rendering.py`

Static response strings for every player-facing command handler. Strings that require runtime
substitution use Python `str.format()` placeholders (e.g. `{time}`, `{verb}`, `{target}`).
Multi-line values use YAML folded scalars (`>-`), which collapse internal newlines to single
spaces and strip the trailing newline. Literal-block scalars (`|` or `|-`) preserve newlines
exactly.

### Top-level key

```
responses:
  <command_group>:
    <response_key>: "string" | folded-scalar | literal-block
```

### Sections

#### `responses.move`

Movement-related feedback strings. Used by `game/player_movement.py` and
`game/movement_validation.py`.

| Key                     | Description                                                         |
| ----------------------- | ------------------------------------------------------------------- |
| `no_exit`               | Player tries a direction with no exit (`null` in rooms.yaml).       |
| `blocked`               | Generic blocked-path message (sentinel `null` destination).         |
| `lobby_forward_blocked` | Specific message for the `__lobby_forward_blocked__` sentinel.      |
| `lobby_back_blocked`    | Specific message for the `__lobby_back_blocked__` sentinel.         |
| `hands_not_washed`      | Player tries to leave the bathroom before washing hands (phase 0).  |
| `hands_still_soapy`     | Player tries to leave bathroom with soap still on hands (phase 1).  |
| `wrong_4way`            | Wrong-direction feedback at the 4-way intersection (Step 1 puzzle). |
| `wrong_janitor`         | Wrong-direction feedback at the janitor hallway (Step 3 puzzle).    |

#### `responses.look`

Examine/look response strings. Used by `game/player_commands.py`.

| Key                  | Description                                                     |
| -------------------- | --------------------------------------------------------------- |
| `mirror_fogged`      | Default mirror description when clue is not yet visible.        |
| `sink_clean`         | Sink description when hands are already clean (phase 4).        |
| `sink_running_rinse` | Sink description when water is running and no soap yet.         |
| `sink_running_stop`  | Sink description when water is running and hands are rinsed.    |
| `sink_off`           | Sink description when water is off and hands are not yet clean. |

#### `responses.read`

Read-verb response strings. Used by `game/player_commands.py`.

| Key             | Description                                                                  |
| --------------- | ---------------------------------------------------------------------------- |
| `no_target`     | Player types `READ` with no target.                                          |
| `detour_sign`   | Reading the detour sign in the lobby.                                        |
| `mirror_fogged` | Trying to read the mirror before it is cleared.                              |
| `generic`       | Fallback for readable items with no specific text. Supports `{item}`.        |
| `not_here`      | Player tries to read something not present in the room. Supports `{target}`. |

#### `responses.open`

| Key         | Description                                                    |
| ----------- | -------------------------------------------------------------- |
| `no_target` | `OPEN` with no argument.                                       |
| `blocked`   | Trying to open something that won't open. Supports `{target}`. |

#### `responses.knock`

| Key         | Description                                        |
| ----------- | -------------------------------------------------- |
| `no_target` | `KNOCK` with no argument.                          |
| `no_answer` | Knocking on a door or object. Supports `{target}`. |

#### `responses.soap`

Soap-dispenser interaction. Used by `game/bathroom.py`.

| Key               | Description                                      |
| ----------------- | ------------------------------------------------ |
| `no_location`     | `SOAP HANDS` outside the bathroom.               |
| `already_clean`   | Hands already clean (phase 4).                   |
| `already_applied` | Soap already on hands (phase 1).                 |
| `wrong_phase`     | Attempting to apply soap in an unexpected phase. |
| `applied`         | Soap successfully applied.                       |

#### `responses.rinse`

Rinse-hands interaction. Used by `game/bathroom.py`.

| Key               | Description                                               |
| ----------------- | --------------------------------------------------------- |
| `no_location`     | `RINSE HANDS` outside the bathroom.                       |
| `no_soap`         | Trying to rinse before applying soap.                     |
| `already_clean`   | Hands already clean.                                      |
| `phase_0`         | First rinse attempt — water cuts off before fully rinsed. |
| `phase_2`         | Second rinse attempt — hands successfully rinsed.         |
| `phase_1_wrong`   | Trying to rinse while water is off (first wrong attempt). |
| `phase_1_wrong_2` | Second wrong attempt at rinse with water off.             |
| `phase_1_wrong_3` | Third wrong attempt — hint with full sequence.            |
| `phase_done`      | Hands rinsed but not yet finished; prompt to `STOP`.      |

#### `responses.stop`

Stop/pull-back-from-sink interaction. Used by `game/bathroom.py`.

| Key             | Description                                                         |
| --------------- | ------------------------------------------------------------------- |
| `no_location`   | `STOP` outside the bathroom.                                        |
| `already_clean` | Sink already off and hands clean.                                   |
| `phase_1`       | Pulling back after water cut off — sensor resets, water comes back. |
| `phase_3`       | Pulling back after final rinse — hands clean, mirror clue revealed. |
| `phase_0`       | Pulling back before soap applied — no-op, water keeps running.      |
| `fallback`      | Generic pull-back response for unexpected phase values.             |

#### `responses.listen`

| Key              | Description                                         |
| ---------------- | --------------------------------------------------- |
| `silence`        | `LISTEN` in any room without ambient audio.         |
| `janitor_prefix` | Prefix line before the janitor's song chorus lines. |

#### `responses.check`

`CHECK <target>` command. Supports `{time}` placeholder for watch/inventory checks.

| Key     | Description                                                   |
| ------- | ------------------------------------------------------------- |
| `watch` | Checking the watch. Supports `{time}`.                        |
| `phone` | Checking the phone.                                           |
| `other` | Fallback for unrecognised check targets. Supports `{target}`. |

#### `responses.inventory`

Inventory command and item-interaction responses.

| Key            | Description                                                     |
| -------------- | --------------------------------------------------------------- |
| `list_prefix`  | Header line before the item list.                               |
| `empty`        | Player somehow has no items.                                    |
| `drop`         | Player tries to drop any item.                                  |
| `backpack`     | Player tries to use/open backpack.                              |
| `phone`        | Player tries to use phone.                                      |
| `keys`         | Player tries to use keys.                                       |
| `wallet`       | Player tries to use wallet.                                     |
| `watch`        | Player uses watch via inventory. Supports `{time}`.             |
| `not_carrying` | Player references an item they don't have. Supports `{target}`. |

#### `responses.quit`

| Key        | Description                            |
| ---------- | -------------------------------------- |
| `farewell` | Message printed when the player quits. |

#### `responses.unknown`

| Key             | Description                              |
| --------------- | ---------------------------------------- |
| _(root string)_ | Unknown-verb message. Supports `{verb}`. |

#### `responses.help`

| Key       | Description                                                 |
| --------- | ----------------------------------------------------------- |
| `header`  | "Available commands:" header.                               |
| `entries` | List of command-description strings shown under the header. |

#### `responses.bathroom_status`

Status line shown at the top of the bathroom room description (injected by
`GameEngine._bathroom_status()`).

| Key           | Phase | Description                        |
| ------------- | ----- | ---------------------------------- |
| `clean`       | 4     | Hands clean, sink off.             |
| `soap_needed` | 0     | Water running, no soap yet.        |
| `soapy`       | 1     | Water running, soap applied.       |
| `water_cut`   | 1     | Water off, hands soapy.            |
| `water_back`  | 2     | Water back on after reset.         |
| `final_rinse` | 3     | Water still running, hands rinsed. |

#### `responses.ambient`

| Key                   | Description                                                  |
| --------------------- | ------------------------------------------------------------ |
| `janitor_hint_prefix` | Prefix shown before janitor song chorus in room description. |

#### `responses.intro`

Intro/splash-screen strings used by `GameEngine._intro_banner_lines()` and `CursesEngine`.

| Key               | Description                                     |
| ----------------- | ----------------------------------------------- |
| `ascii_art`       | Multi-line ASCII art box (literal-block `\|-`). |
| `title`           | Game title line.                                |
| `opening`         | First line of opening narration.                |
| `problem`         | Second line of opening narration.               |
| `teacher`         | Teacher's voice line (folded scalar).           |
| `curses_subtitle` | Subtitle shown in the curses intro panel.       |
| `help_hint`       | "Type HELP…" hint line.                         |

#### `responses.ui_labels`

Labels for the curses split-pane UI panels. Loaded into a shared `UI` dict by
`game/curses_engine.py` and `game/curses_rendering.py`. Changing these values updates all
visible panel headings without modifying Python code.

| Key                  | Panel/heading it controls                             |
| -------------------- | ----------------------------------------------------- |
| `header_time_prefix` | Prefix before the time counter in the top header bar. |
| `panel_room`         | Title of the room-description (left) panel.           |
| `panel_log`          | Title of the command-log (right) panel.               |
| `section_details`    | "DETAILS" heading inside the room panel.              |
| `section_clue`       | "CLUE" heading inside the room panel.                 |
| `section_exits`      | "EXITS" heading inside the room panel.                |
| `section_items`      | "YOU NOTICE" heading inside the room panel.           |

#### `responses.end`

End-game screens. Used by `GameEngine._end_lines()`.

| Key             | Condition                      | Description                              |
| --------------- | ------------------------------ | ---------------------------------------- |
| `won_early`     | Arrived with ≥ 5 min remaining | Player arrived early — punchline ending. |
| `won`           | Arrived with < 5 min remaining | Player made it just in time.             |
| `lost`          | `time_remaining == 0`          | Time expired.                            |
| `press_any_key` | All endings                    | Exit prompt line.                        |

---

## rooms.yaml

**Loaded by:** `game/world.py` → `build_world()`

All room definitions. The loader validates required fields, then clones each entry into a
`Room` object (see `game/room.py`). Mutable fields (`exits`, `items`, `attributes`) are
deep-copied on each `build_world()` call so multiple test instances don't share state.

### Room entry structure

```yaml
- room_id: <string> # unique key used throughout the engine
  name: <string> # short display name shown in the UI header/panel
  description: <string> # full prose description; shown on room entry
  exits: # directional exit map; value is destination room_id
    forward: <room_id|null|sentinel>
    back: <room_id|null|sentinel>
    left: <room_id|null|sentinel>
    right: <room_id|null|sentinel>
  items: # optional; map of item_id -> display name
    <item_id>: <string>
  attributes: # optional; arbitrary key/value pairs for game logic
    <key>: <value>
  type: structural | flavor # used to build FLAVOR_ROOM_POOL
```

### Exit values

| Value                       | Meaning                                                           |
| --------------------------- | ----------------------------------------------------------------- |
| `<room_id>`                 | Normal exit to the named room.                                    |
| `null`                      | Direction exists but leads nowhere (blocked or wired at runtime). |
| `__lobby_forward_blocked__` | Sentinel — displays `responses.move.lobby_forward_blocked`.       |
| `__lobby_back_blocked__`    | Sentinel — displays `responses.move.lobby_back_blocked`.          |

Exits marked `null` in this file are wired dynamically by puzzle routing logic in
`game/movement_routing.py` each time the player enters a puzzle room.

### Room types

| Type         | Description                                                                  |
| ------------ | ---------------------------------------------------------------------------- |
| `structural` | Part of the critical path; always present in the world.                      |
| `flavor`     | Wrong-way detour room; sampled randomly into the wrong-way chain at runtime. |

### Structural rooms (critical path)

| `room_id`                | Display name       | Notes                                             |
| ------------------------ | ------------------ | ------------------------------------------------- |
| `lobby`                  | Building Lobby     | Starting room. Two sentinel exits, one real exit. |
| `hallway_approach`       | Detour Hallway     | Linear path to the first puzzle node.             |
| `intersection_4way`      | 4-Way Intersection | **Step 1 puzzle node.** Exits wired at runtime.   |
| `intersection_3way`      | 3-Way Junction     | Leads to the bathroom; sides wired at runtime.    |
| `bathroom`               | Restroom           | **Step 2 puzzle node.** Hand-washing mini-puzzle. |
| `intersection_3way_exit` | 3-Way Junction     | Post-bathroom junction; exits wired at runtime.   |
| `hallway_janitor`        | Janitor's Hallway  | **Step 3/4 puzzle node.** Janitor song clue.      |
| `hallway_final`          | Final Stretch      | Linear path to the win room.                      |
| `room_314`               | Room 314           | Win condition. Setting `is_win_room: true`.       |

### Flavor rooms (wrong-way pool)

Flavor rooms are sampled randomly by `movement_routing.build_room_entry_handlers()` to build a
"wrong-way chain" when the player goes the wrong direction at the 4-way intersection. After
traversing the chain they are routed back to the junction.

| `room_id`               | Display name   |
| ----------------------- | -------------- |
| `flavor_copy_room`      | Copy Room      |
| `flavor_faculty_office` | Faculty Office |
| `flavor_study_lounge`   | Study Lounge   |
| `flavor_stairwell`      | Stairwell      |
| `flavor_classroom_195`  | Classroom 195  |
| `flavor_water_fountain` | Hallway Nook   |

### `attributes` keys reference

The following attribute keys are used by game logic. Not every room uses all keys.

| Key                   | Type   | Used in           | Description                                     |
| --------------------- | ------ | ----------------- | ----------------------------------------------- |
| `one_way`             | `bool` | `lobby`           | Informational; not currently read by engine.    |
| `is_puzzle_node`      | `bool` | puzzle rooms      | Tags the room as a puzzle step location.        |
| `puzzle_step`         | `int`  | puzzle rooms      | Which step this room belongs to (1–4).          |
| `is_win_room`         | `bool` | `room_314`        | Triggers win condition on entry.                |
| `janitor_present`     | `bool` | `hallway_janitor` | Enables janitor song hint rendering.            |
| `song_heard`          | `bool` | `hallway_janitor` | Set `true` when the player listens to the song. |
| `sink_running`        | `bool` | `bathroom`        | Water is currently on.                          |
| `hands_wet`           | `bool` | `bathroom`        | Hands were placed under water.                  |
| `hands_soapy`         | `bool` | `bathroom`        | Soap has been applied.                          |
| `hands_rinsed`        | `bool` | `bathroom`        | Hands have been rinsed.                         |
| `stalls_locked`       | `bool` | `bathroom`        | All stalls are locked (flavour).                |
| `mirror_clue_visible` | `bool` | `bathroom`        | Mirror clue revealed after final rinse.         |

### `items` reference

Items are the subset of room contents the player can `LOOK AT`, `READ`, or interact with.

| `item_id`     | Room                   | Display name                |
| ------------- | ---------------------- | --------------------------- |
| `detour_sign` | `lobby`                | a hand-lettered detour sign |
| `sink`        | `bathroom`             | a motion-sensor sink        |
| `mirror`      | `bathroom`             | a large wall mirror         |
| `paper`       | `flavor_classroom_195` | a face-down sheet of paper  |

---

## events.yaml

**Loaded by:** `game/event.py` → `load_events()`

Ambient narrative events that fire automatically based on game state. The `EventQueue` checks
every registered event after each player action and prints the `message` of the first event
whose `condition` evaluates to `True`.

### Event entry structure

```yaml
- event_id: <string>     # unique identifier
  message: <string>      # text printed to the player when the event fires
  condition:             # declarative condition spec (see below)
    type: <condition_type>
    ...
```

### Condition types

| `type`            | Additional fields     | Evaluates to `True` when…                   |
| ----------------- | --------------------- | ------------------------------------------- |
| `time_range`      | `gt: int`, `lte: int` | `gt < state.time_remaining <= lte`          |
| `move_count_eq`   | `value: int`          | `state.move_count == value`                 |
| `move_count_gte`  | `value: int`          | `state.move_count >= value`                 |
| `location`        | `room_id: str`        | `state.current_room_id == room_id`          |
| `wrong_turns_gte` | `value: int`          | `state.wrong_turns >= value`                |
| `all`             | `conditions: list`    | All sub-conditions are `True` (logical AND) |

Sub-conditions inside `all` use the same type/field structure as top-level conditions.

### Events catalog

#### Time-based warnings

| `event_id`          | Fires at (`time_remaining`) | Message summary                    |
| ------------------- | --------------------------- | ---------------------------------- |
| `time_warning_5min` | 286–300 s                   | Phone buzzes — 5-minute warning.   |
| `time_warning_3min` | 166–180 s                   | Lights flicker — 3-minute warning. |
| `time_warning_2min` | 106–120 s                   | Cold air vent — 2-minute warning.  |

#### Move-count tension beats

| `event_id`               | `move_count` | Message summary                                    |
| ------------------------ | ------------ | -------------------------------------------------- |
| `tension_door_closes`    | 3            | A door closes somewhere.                           |
| `ominous_footsteps`      | 5            | Footsteps behind you that vanish.                  |
| `tension_footsteps_stop` | 8            | Footsteps that stop when you stop.                 |
| `ominous_watched`        | 10           | You feel watched.                                  |
| `tension_light_buzzes`   | 13           | The light above you dims and flickers.             |
| `ominous_whisper`        | 15           | An unintelligible whisper.                         |
| `tension_marker_smell`   | 20           | Smell of dry-erase markers — classrooms are close. |

#### Location-based atmosphere

| `event_id`                  | Trigger                                  | Message summary                 |
| --------------------------- | ---------------------------------------- | ------------------------------- |
| `lobby_ceiling_tiles`       | `lobby` + `move_count >= 1`              | Ceiling tiles are misaligned.   |
| `hallway_no_signal`         | `hallway_approach`                       | No phone signal, battery at 3%. |
| `intersection_door_numbers` | `intersection_4way` + `wrong_turns >= 1` | Door numbers keep changing.     |
| `bathroom_stall_click`      | `bathroom`                               | Stall doors click softly.       |
| `janitor_same_spot`         | `hallway_janitor`                        | Janitor mopping the same patch. |

---

## puzzle.yaml

**Loaded by:** `game/puzzle.py`

Narrative text templates for the three-step puzzle clue system. All values are folded scalars
(`>-`) that resolve to a single paragraph string.

### `step1_clue_templates`

Keyed by **clue type**. The correct direction for Step 1 is chosen randomly by
`puzzle.step1_roll()` from `["left", "right", "forward"]`. The clue type is also chosen
randomly from the keys of this section.

Placeholder tokens:

| Token        | Substituted with                                                  |
| ------------ | ----------------------------------------------------------------- |
| `{correct}`  | The correct direction (e.g. `"left"`).                            |
| `{opposite}` | The opposite direction (e.g. `"right"` when correct is `"left"`). |

| Clue type key | Visual device                                                       |
| ------------- | ------------------------------------------------------------------- |
| `light`       | A flickering fluorescent light marks the _wrong_ hallway.           |
| `sign`        | An orange CS-club flyer with an arrow points the correct way.       |
| `shadow`      | A fleeting shadow slips around the corner in the correct direction. |

### `step2_mirror_text`

A single folded-scalar string. Used by `puzzle.step2_mirror_text()`. The correct direction for
Step 2 is the exit direction from `intersection_3way` that leads toward the janitor's hallway,
seeded by `puzzle.step2_roll()`.

Placeholder tokens:

| Token         | Substituted with                                                      |
| ------------- | --------------------------------------------------------------------- |
| `{backwards}` | The direction string reversed character-by-character (e.g. `"TFEL"`). |
| `{direction}` | The correct direction in uppercase (e.g. `"LEFT"`).                   |

---

## songs.yaml

**Loaded by:** `game/puzzle.py` → `step3_roll()` (via `game.load_yaml_data()`)

The pool of songs the janitor hums. Step 3 (`step3_roll()`) randomly picks one entry from this
list; its `direction` value becomes `state.active_clues["step3_correct_dir"]` and its `chorus`
is printed when the player types `LISTEN` in the janitor's hallway.

### Entry structure

```yaml
- direction: left | right # the direction word hidden in this song
  title: <string> # song title (shown as a header line when listening)
  chorus: | # literal-block scalar; exact chorus lyrics
    <line 1>
    <line 2>
    ...
```

### `direction` values

| Value   | Meaning                       |
| ------- | ----------------------------- |
| `left`  | The Step 3 answer is `LEFT`.  |
| `right` | The Step 3 answer is `RIGHT`. |

> **Note:** `forward` and `back` are intentionally absent from the song pool. The Step 3
> direction is constrained to `left` or `right` so the janitor's lyrical clue is unambiguous.

### Songs catalog

#### Left songs

| Title                            |
| -------------------------------- |
| I Left My Heart in San Francisco |
| Left Outside Alone               |
| What's Left of Me                |
| Left to My Own Devices           |
| Nothing Left to Lose             |
| I Left My Wallet in El Segundo   |
| Left of Center                   |
| Left in the Dark                 |
| My Baby Left Me                  |
| The Girl I Left Behind Me        |

#### Right songs

| Title                            |
| -------------------------------- |
| Right Round                      |
| Right Here Waiting               |
| Right Now                        |
| The Right Stuff                  |
| Right Back Where We Started From |
| Feels So Right                   |
| Right Hand Man                   |
| Do It Right                      |
| Treat You Right                  |
| Right As Rain                    |
