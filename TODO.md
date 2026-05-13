<!-- working-on: Identify opportunities across the codebase to simplify, refactor, or remove redundant and overlapping functions in ways that reduce complexity and improve maintainability. Include tests, CSS, and dev tools/scripts. Update callsites to use the simplified flow, then remove the old code and any related tests without preserving fallbacks, shims, aliases, or wrappers for removed or consolidated functions. Small refactors have largely been exhausted and remaining ones are likely constrained by complexity boundaries, so prioritize larger refactors with maximum impact, especially those spanning multiple files or modules. Split modules over 500 lines (excluding docstrings/comments). Be deliberate about complexity when deciding whether to inline small helpers, combine related helpers, or split large ones. Maintain the default complexity caps enforced by linters; do not raise limits, add ignores, or otherwise bypass those constraints to make a refactor fit. Ensure refactors are thoroughly tested and that the test suite remains comprehensive and robust throughout. Update documentation to reflect the new code structure and any resulting changes in functionality or usage. Treat this as a major, multi-pass effort requiring careful attention to detail to produce a clean, modern codebase without legacy artifacts. -->

# Project Tasklist

- [x] implement shortcuts for movement commands (f for forward, b for back, l for left, r for
      right)

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
    - [x] Remove the dead flat-layout `game/engine.py` and `game/janitor.py` modules, update
          stale doc/test references to the nested package paths, and validate the
          package-layout cleanup with focused core, engine, curses, and puzzle helper suites.
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
