# B2 brute-force checker

Offline reference checker for 3×3 and 4×4 boards, owned by Gia Hân and reviewed by
Kiên (`tonthatkien`). Uses `logic.semantic.evaluate(Clue, assignment, n)`;
does not import DPLL or the CNF encoder. No extra Python dependencies.

## Status and dependency

At base commit `0f950c0af54d87299debdd3f8c84cc386c635fdd`, D5's evaluator is a stub
raising `NotImplementedError`. B2 search mechanics can be tested with explicitly
labelled test doubles. **Real puzzle results and acceptance remain blocked by D5.**
PARITY and COMPARE integration also requires D6. The real integration tests skip
while the FACT readiness probe raises `NotImplementedError`. Once FACT works,
failures in other clue implementations are test failures, not silently skipped.

B1's merged `docs/INTERFACES.md` defines `target`, `SAME_STATUS`, `DIFFERENT_STATUS`,
`cell1/cell2`, `number`, `letter`, `list`, and `region1/region2`. The current
`engine.clue` implementation still documents/resolves the old schema and its
validator is a stub. B2 validates the agreed JSON schema locally, using the actual
`Clue` and `clue_from_dict`, without changing that shared module or translating
into its obsolete schema. This boundary needs review when A2/D5 are integrated.

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
exactly N² characters, one valid clue per character, alphabetically ordered names
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

Enumeration, counting, face-up constraints, validation, immutability, failure
propagation, CLI output and independence tests use no evaluator or explicit
test doubles. They do not certify D5 semantics. Separate real integration tests
cover all eight clue types, both statuses, all region types, counting boundaries,
parity at zero, comparison operators, overlapping regions, 4×4, and `p01.json`.
Expected counts come from combinatorics and direct truth values. The sample's
expected model is derived from its clues, not its hidden labels; it remains an
unverified expectation until D5 actually runs. Do not claim a sample result from
these skipped tests.

PR acceptance additionally requires real integration, review approval and CI.
The AI usage log is awaiting the user's completion and authorization; it is not
included in this change. No merge is authorized.
