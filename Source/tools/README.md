# B2 brute-force checker

Offline reference checker for 3×3 and 4×4 boards, owned by Gia Hân with assigned
reviewer Kiên (`tonthatkien`). Uses `logic.semantic.evaluate(Clue, assignment, n)`;
does not import DPLL or the CNF encoder. No extra Python dependencies.

## Status and dependency

D5 and D6 were merged in [PR #10](https://github.com/tonthatkien/Griductive-Solver/pull/10),
at main commit `9d65892e6aec5309d2cd175ecd8cc86e26e1e576`. B2 is tested with that
real evaluator for all six core clues and both extensions. Integration tests are
mandatory: missing or broken evaluator implementations now fail rather than skip.

Clues use the actual `Clue`, `clue_from_dict`, shared `validate_clue` and clue-type
constants from `engine.clue`. B2 validates puzzle shape and caller-supplied
assignments; it no longer duplicates the shared region/clue schema validator.
Character names must increase strictly by `casefold()` in row-major cell order,
matching the current loader; duplicate names, including case variants, are rejected.

## Usage

Run in `Source/`, with Python 3.10+ (`python3` if `python` is unavailable):

```bash
python -m tools.brute_force data/puzzles_3x3/p01.json
python -m tools.brute_force data/puzzles_3x3/p01.json --stop-after-two
python -m unittest -v tests.test_brute_force
python -m unittest discover -s tests -t .
python -m compileall tools tests
```

The CLI prints JSON on success. Invalid input or an unavailable evaluator exits
with code 2 and prints an error to stderr, with no fake UNSAT/uniqueness result.

```python
from tools.brute_force import check_puzzle, count_solutions, iter_assignments

result = check_puzzle(puzzle)  # JSON-format dictionary; full clue set
# To check an explicitly chosen subset (including an empty set):
public_result = count_solutions(revealed_clues, 3, known_statuses={"A1": False})
```

`check_puzzle` checks all clues, including face-down clues, plus the statuses of
`initially_revealed` cells. It is intended for complete-puzzle validation, not
gameplay. Other stored `criminal` labels are checked only for Boolean schema
validity; their values never constrain the search. Hidden-solution comparison is
not performed. The input puzzle and clue dictionaries remain unchanged.

`count_solutions` accepts an iterable of `Clue` objects and a mapping of selected
public Boolean facts. An empty clue set is valid here. `check_puzzle` requires
exactly N² characters, one valid clue per character, distinct alphabetically ordered names
in row-major cell order, and nonempty, distinct, valid initially revealed cells.
Schema errors raise `ValueError`. Uniqueness is a check result, not an input
precondition: inconsistent and ambiguous puzzles must be inspectable.

## Result and stopping rules

`CheckResult` includes `assignments_checked`, `satisfying_assignments`, `status`
(`UNSAT`, `UNIQUE`, `MULTIPLE`), `unique_solution`, `exhaustive`, `runtime` in
seconds, and the property `count_is_exact`. The CLI includes that property in JSON.

The default search considers all 512 or 65,536 assignments, including those
rejected by public facts. Counts are exact. Optional `stop_after_two=True` stops
at the second model: `satisfying_assignments=2` is a lower bound whenever
`exhaustive=False`. A second model on the final assignment still gives an exact
count. A single model is returned only after exhaustive search proves uniqueness.
UNSAT also requires exhaustion. No arbitrary model is presented as a unique one.

Evaluator exceptions propagate through the API. Non-Boolean evaluator results
raise `TypeError`. Every clue is evaluated for each assignment compatible with
public facts, even after a preceding clue returns false; unsupported clue errors
cannot be hidden by short-circuiting. Generated assignments contain exactly N²
Boolean values. `validate_assignment` checks external complete assignments.

## Correctness and cost

For v=N², `product((False, True), repeat=v)` enumerates each of the 2^v Boolean
tuples exactly once. Zipping each tuple to `board.all_cells(n)` is a bijection to
complete cell assignments. Every tuple is visited unless the caller explicitly
requests stopping after the second model. A candidate is counted iff every
selected public fact matches and every semantic evaluation is true. Therefore
exhaustive counts establish UNSAT, uniqueness or multiplicity; finding two models
alone already proves multiplicity. Neither hidden labels nor another solver are
used to exclude candidates.

For m clues and semantic cost c per clue, time is O(2^v × (v + m×c)). Region-based
evaluation may itself cost O(v). Auxiliary space is O(v + total clue input size):
the checker retains copied clues, public facts, one candidate and one first model,
not all satisfying assignments. The test suite intentionally retains signatures
to verify no duplicate enumeration; this is not production search memory usage.
At 4×4 at most 65,536 assignments are checked; evaluator cost dominates. Use early
stopping only when proof of multiplicity suffices. Exact counts and proofs of
zero/one model require exhaustive enumeration. 5×5 is rejected (33,554,432
assignments); DPLL stress testing belongs to later tasks.

## Verification boundary

Enumeration, search mechanics and error propagation tests use no evaluator or
explicitly labelled test doubles. Separate mandatory real integration tests cover
all eight clue types, both statuses, all region types, counting boundaries, parity
at zero, comparison operators, overlapping regions, and all three solution classes
on full 3×3/4×4 puzzle fixtures. They also exercise the actual CLI, immutability,
hidden-label independence, and the current engine's public KB. No DPLL or encoder
is used as the oracle: expected counts come from combinatorics and truth tables.

With the merged evaluator, `p01.json` has exactly **one** model after all **512**
assignments are checked. Criminal cells are **A1, B2, C2, C3**; all others are
Innocent. Its initial public KB alone admits **16** models. Flipping only face-down
stored labels leaves the computed solution unchanged. These are real integration
results, not mock outputs. The expected sample model was derived from the clues
before being verified by the checker.

Validation on this base: **47 B2 tests**, including **14 dedicated real integration
tests**, pass without skips. Full repository tests and smoke results are recorded
separately in the review report. The GUI entry point on this main base remains an
unimplemented F1 stub, outside B2; checker CLI success does not certify the GUI.

PR acceptance additionally requires review approval and CI.
The AI usage log is awaiting the user's completion and authorization; it is not
included in this change. No merge is authorized.
