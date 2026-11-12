"""B2: deterministic, exhaustive reference checker for 3x3 and 4x4 puzzles.

Uses only semantic.evaluate, never a SAT solver or an encoder. JSON validation
follows docs/INTERFACES.md (B1); engine.clue's current validator is still a stub
and its region resolver still uses the older schema. Do not translate clues to
that schema: D5 must consume the agreed contract. Evaluator errors propagate.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Iterator, Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
from time import perf_counter
from typing import Literal

from engine import board
from engine.clue import Clue, clue_from_dict
from engine.game_state import CRIMINAL, INNOCENT
from logic.semantic import evaluate

SUPPORTED_SIZES = (3, 4)
COUNT_TYPES = ("EXACTLY", "AT_LEAST", "AT_MOST")
PAIR_TYPES = ("SAME_STATUS", "DIFFERENT_STATUS")
CLUE_TYPES = ("FACT", *PAIR_TYPES, *COUNT_TYPES, "PARITY", "COMPARE")
COMPARE_OPS = ("GT", "GE", "EQ", "LE", "LT")
UNSAT, UNIQUE, MULTIPLE = "UNSAT", "UNIQUE", "MULTIPLE"
Assignment = dict[str, bool]


@dataclass(frozen=True)
class CheckResult:
    """Count is exact iff exhaustive; otherwise satisfying_assignments is a lower bound.

    assignments_checked includes assignments rejected by public known statuses.
    unique_solution is populated only after a complete search finds one model.
    runtime is elapsed seconds, including input validation, measured by perf_counter.
    """

    assignments_checked: int
    satisfying_assignments: int
    status: Literal["UNSAT", "UNIQUE", "MULTIPLE"]
    unique_solution: Assignment | None
    exhaustive: bool
    runtime: float

    @property
    def count_is_exact(self) -> bool:
        """Whether satisfying_assignments counts every model, rather than a lower bound."""
        return self.exhaustive


def _validate_size(n: int) -> None:
    if type(n) is not int or n not in SUPPORTED_SIZES:
        raise ValueError("B2 supports only integer board sizes 3 and 4")


def _validate_cell(cell: object, n: int) -> None:
    if not isinstance(cell, str) or cell not in board.all_cells(n):
        raise ValueError(f"Invalid cell for {n}x{n}: {cell!r}")


def _validate_status(status: object) -> None:
    if status not in (CRIMINAL, INNOCENT):
        raise ValueError(f"Invalid status: {status!r}")


def _region_cells(region: object, n: int) -> list[str]:
    if not isinstance(region, dict):
        raise ValueError("Region must be an object")
    kind = region.get("type")
    if kind == "row":
        number = region.get("number")
        if type(number) is not int or not 1 <= number <= n:
            raise ValueError("Row number must be an integer in 1..n")
        return board.row_cells(n, number)
    if kind == "col":
        letter = region.get("letter")
        if not isinstance(letter, str) or letter not in board.COLS[:n] or len(letter) != 1:
            raise ValueError("Column letter must be uppercase and in bounds")
        return board.col_cells(n, letter)
    if kind == "neighbors":
        _validate_cell(region.get("cell"), n)
        return board.neighbor_cells(n, region["cell"])
    if kind == "list":
        cells = region.get("cells")
        if not isinstance(cells, list) or not cells:
            raise ValueError("Explicit region must be a nonempty list")
        for cell in cells:
            _validate_cell(cell, n)
        if len(set(cells)) != len(cells):
            raise ValueError("Region contains duplicate cells")
        return cells
    raise ValueError(f"Unsupported region type: {kind!r}")


def _validate_clue(clue: Clue, n: int) -> None:
    if not isinstance(clue, Clue) or not isinstance(clue.params, dict):
        raise ValueError("Each constraint must be a Clue with dictionary params")
    _validate_cell(clue.owner, n)
    if not isinstance(clue.type, str) or clue.type not in CLUE_TYPES:
        raise ValueError(f"Unsupported clue type: {clue.type!r}")
    params = clue.params
    if "status" in params:
        _validate_status(params["status"])
    if clue.type == "FACT":
        _validate_cell(params.get("target"), n)
        _validate_status(params.get("status"))
    elif clue.type in PAIR_TYPES:
        for key in ("cell1", "cell2"):
            _validate_cell(params.get(key), n)
        if params["cell1"] == params["cell2"]:
            raise ValueError("Pair clues must reference distinct cells")
    elif clue.type == "COMPARE":
        for key in ("region1", "region2"):
            _region_cells(params.get(key), n)
        if params.get("op") not in COMPARE_OPS:
            raise ValueError("Invalid comparison operator")
    else:
        cells = _region_cells(params.get("region"), n)
        if clue.type in COUNT_TYPES:
            count = params.get("k")
            if type(count) is not int or not 0 <= count <= len(cells):
                raise ValueError("k must be an integer in 0..region size")
        elif params.get("parity") not in ("EVEN", "ODD"):
            raise ValueError("Invalid parity")


def _prepare_clue(clue: Clue, n: int) -> Clue:
    _validate_clue(clue, n)
    prepared = deepcopy(clue)
    if prepared.type in (*COUNT_TYPES, "PARITY", "COMPARE"):
        prepared.params.setdefault("status", CRIMINAL)
    return prepared


def _known_statuses(statuses: Mapping[str, bool] | None, n: int) -> Assignment:
    if statuses is None:
        return {}
    if not isinstance(statuses, Mapping):
        raise ValueError("known_statuses must map cells to Boolean values")
    for cell, value in statuses.items():
        _validate_cell(cell, n)
        if type(value) is not bool:
            raise ValueError("Known statuses must be Boolean, not integers or strings")
    return dict(statuses)


def validate_assignment(assignment: Mapping[str, bool], n: int) -> None:
    """Reject incomplete assignments, extra cells and non-Boolean values with ValueError."""
    _validate_size(n)
    checked = _known_statuses(assignment, n)
    if set(checked) != set(board.all_cells(n)):
        raise ValueError("Assignment must contain every cell exactly once")


def iter_assignments(n: int) -> Iterator[Assignment]:
    """Enumerate fresh, complete Boolean assignments in deterministic row-major order.

    False precedes True. No partial assignment, hidden-label pruning or sampling is used.
    """
    _validate_size(n)
    cells = board.all_cells(n)
    return (dict(zip(cells, values)) for values in product((False, True), repeat=n * n))


def _satisfies(clues: tuple[Clue, ...], assignment: Assignment, n: int) -> bool:
    valid = True
    for clue in clues:
        verdict = evaluate(clue, assignment, n)
        if type(verdict) is not bool:
            raise TypeError("semantic.evaluate must return bool")
        # Evaluate every clue, even after a false result, to expose unsupported clues.
        valid = verdict and valid
    return valid


def count_solutions(
    clues: Iterable[Clue],
    n: int,
    *,
    known_statuses: Mapping[str, bool] | None = None,
    stop_after_two: bool = False,
) -> CheckResult:
    """Check an explicit constraint set (possibly empty) without accessing a puzzle.

    known_statuses contains only caller-selected public facts, with True = Criminal.
    This API can check a public subset; check_puzzle always uses the full puzzle.
    Default: enumerate all 2**(n*n) assignments. stop_after_two proves multiplicity
    but returns a lower bound unless the last assignment was reached. Evaluator
    exceptions (including NotImplementedError from missing D5/D6) are not UNSAT.

    With v=n*n, m clues and semantic cost c per clue, time is
    O(2**v * (v + m*c)); space is O(v + total clue input size), retaining one model.
    """
    started = perf_counter()
    _validate_size(n)
    if type(stop_after_two) is not bool:
        raise ValueError("stop_after_two must be Boolean")
    prepared = tuple(_prepare_clue(clue, n) for clue in clues)
    known = _known_statuses(known_statuses, n)
    checked = count = 0
    first_model = None
    for assignment in iter_assignments(n):
        checked += 1
        if any(assignment[cell] != status for cell, status in known.items()):
            continue
        if _satisfies(prepared, assignment, n):
            count += 1
            if count == 1:
                first_model = assignment.copy()
            if stop_after_two and count == 2:
                break
    exhaustive = checked == 2 ** (n * n)
    status = UNSAT if count == 0 else UNIQUE if count == 1 else MULTIPLE
    return CheckResult(
        checked, count, status, first_model if count == 1 and exhaustive else None,
        exhaustive, perf_counter() - started,
    )


def _puzzle_clues(puzzle: dict, n: int) -> tuple[list[Clue], Assignment]:
    characters = puzzle.get("characters")
    if not isinstance(characters, list) or len(characters) != n * n:
        raise ValueError("Puzzle must contain exactly n*n characters")
    clues, labels, names = [], {}, {}
    for character in characters:
        if not isinstance(character, dict):
            raise ValueError("Each character must be an object")
        cell = character.get("cell")
        _validate_cell(cell, n)
        if cell in labels:
            raise ValueError(f"Duplicate character cell: {cell}")
        if type(character.get("criminal")) is not bool:
            raise ValueError("Character criminal label must be Boolean")
        for key in ("name", "profession"):
            if not isinstance(character.get(key), str) or not character[key].strip():
                raise ValueError(f"Character {key} must be a nonempty string")
        raw = character.get("clue")
        if not isinstance(raw, dict) or "type" not in raw:
            raise ValueError("Each character must have a clue object with a type")
        clues.append(_prepare_clue(clue_from_dict(cell, raw), n))
        labels[cell], names[cell] = character["criminal"], character["name"]
    ordered_names = [names[cell] for cell in board.all_cells(n)]
    if ordered_names != sorted(ordered_names):
        raise ValueError("Character names must be alphabetical in row-major order")
    revealed = puzzle.get("initially_revealed")
    if not isinstance(revealed, list) or not revealed:
        raise ValueError("initially_revealed must be a nonempty list")
    for cell in revealed:
        _validate_cell(cell, n)
    if len(set(revealed)) != len(revealed):
        raise ValueError("Duplicate initially revealed cell")
    return clues, {cell: labels[cell] for cell in revealed}


def check_puzzle(puzzle: dict, *, stop_after_two: bool = False) -> CheckResult:
    """Check all clues plus initially face-up statuses in a JSON-format puzzle.

    Face-down criminal labels are schema-validated but NEVER constrain the search.
    Does not mutate the input or compare its hidden solution to the computed model.
    Invalid input raises ValueError; UNSAT and MULTIPLE are legitimate check results.
    """
    started = perf_counter()
    if not isinstance(puzzle, dict):
        raise ValueError("Puzzle must be an object")
    n = puzzle.get("n")
    _validate_size(n)
    clues, known = _puzzle_clues(puzzle, n)
    result = count_solutions(clues, n, known_statuses=known, stop_after_two=stop_after_two)
    return CheckResult(
        result.assignments_checked, result.satisfying_assignments, result.status,
        result.unique_solution, result.exhaustive, perf_counter() - started,
    )


def main() -> None:
    """Run from Source with python -m tools.brute_force path/to/puzzle.json."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("puzzle", type=Path)
    parser.add_argument("--stop-after-two", action="store_true", help="Count at least two models")
    args = parser.parse_args()
    try:
        with args.puzzle.open(encoding="utf-8") as stream:
            result = check_puzzle(json.load(stream), stop_after_two=args.stop_after_two)
    except (OSError, ValueError, TypeError, NotImplementedError) as error:
        detail = str(error) or "semantic.evaluate is unimplemented; D5/D6 integration is required"
        parser.exit(2, f"Checker error ({type(error).__name__}): {detail}\n")
    print(json.dumps({**asdict(result), "count_is_exact": result.count_is_exact}, indent=2))


if __name__ == "__main__":
    main()
