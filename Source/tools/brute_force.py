"""B2: deterministic, exhaustive reference checker for 3x3 and 4x4 puzzles.

Uses only semantic.evaluate, never a SAT solver or an encoder. Clue validation
uses engine.clue's shared validator and the agreed docs/INTERFACES.md schema.
Evaluator errors propagate instead of being interpreted as UNSAT.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Iterator, Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from itertools import product
from pathlib import Path
from time import perf_counter
from typing import Literal

from engine import board
from engine.clue import CORE_TYPES, COUNT_TYPES, EXT_TYPES, Clue, clue_from_dict, validate_clue
from engine.constants import CRIMINAL, INCONSISTENT, INNOCENT, STATUSES, UNKNOWN
from engine.game_state import PublicKB
from logic.semantic import evaluate

SUPPORTED_SIZES = (3, 4)
CLUE_TYPES = CORE_TYPES + EXT_TYPES
UNSAT, UNIQUE, MULTIPLE = "UNSAT", "UNIQUE", "MULTIPLE"
Assignment = dict[str, bool]


@dataclass(frozen=True)
class CheckResult:
    """Count is exact iff exhaustive; otherwise satisfying_assignments is a lower bound.

    assignments_checked includes assignments rejected by public known statuses.
    unique_solution is populated only after a complete search finds one model.
    runtime is elapsed seconds, including input validation, measured by perf_counter.
    classifications is complete only after exhaustive search; UNSAT marks every
    cell INCONSISTENT. A partial search returns None, never unproved forced statuses.
    labels_match_solution compares stored labels AFTER search, only in check_puzzle.
    """

    assignments_checked: int
    satisfying_assignments: int
    status: Literal["UNSAT", "UNIQUE", "MULTIPLE"]
    unique_solution: Assignment | None
    exhaustive: bool
    runtime: float
    classifications: dict[str, str] | None = None
    labels_match_solution: bool | None = None

    @property
    def count_is_exact(self) -> bool:
        """Whether satisfying_assignments counts every model, rather than a lower bound."""
        return self.exhaustive


def _validate_size(n: int) -> None:
    if type(n) is not int or n not in SUPPORTED_SIZES:
        raise ValueError("B2 supports only integer board sizes 3 and 4")


def _validate_cell(cell: object, n: int) -> None:
    if not isinstance(cell, str) or not board.is_valid_cell(cell, n):
        raise ValueError(f"Invalid cell for {n}x{n}: {cell!r}")


def _validate_clue(clue: Clue, n: int) -> None:
    if not isinstance(clue, Clue) or not isinstance(clue.params, dict):
        raise ValueError("Each constraint must be a Clue with dictionary params")
    if not isinstance(clue.type, str) or clue.type not in CLUE_TYPES:
        raise ValueError(f"Unsupported clue type: {clue.type!r}")
    validate_clue(clue, n)


def _prepare_clue(clue: Clue, n: int) -> Clue:
    try:
        _validate_clue(clue, n)
    except ValueError as error:
        owner = clue.owner if isinstance(clue, Clue) else "?"
        raise ValueError(f"character {owner}: invalid clue: {error}") from error
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


def _evaluate_clue(clue: Clue, assignment: Assignment, n: int) -> bool:
    verdict = evaluate(clue, assignment, n)
    if type(verdict) is not bool:
        raise TypeError("semantic.evaluate must return bool")
    return verdict


def _satisfies(clues: tuple[Clue, ...], assignment: Assignment, n: int) -> bool:
    return all(_evaluate_clue(clue, assignment, n) for clue in clues)


def _classifications(seen: dict[str, int], exhaustive: bool) -> dict[str, str] | None:
    if not exhaustive:
        return None
    # Each bit records whether a cell was observed Innocent or Criminal in any model.
    statuses = {0: INCONSISTENT, 1: INNOCENT, 2: CRIMINAL, 3: UNKNOWN}
    return {cell: statuses[mask] for cell, mask in seen.items()}


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
    smoke = dict.fromkeys(board.all_cells(n), False)
    for clue in prepared:
        # Check each evaluator independently once; this is not a searched candidate.
        _evaluate_clue(clue, smoke, n)
    seen = dict.fromkeys(smoke, 0)
    checked = count = 0
    first_model = None
    for assignment in iter_assignments(n):
        checked += 1
        if any(assignment[cell] != status for cell, status in known.items()):
            continue
        if _satisfies(prepared, assignment, n):
            count += 1
            for cell, value in assignment.items():
                seen[cell] |= 2 if value else 1
            if count == 1:
                first_model = assignment.copy()
            if stop_after_two and count == 2:
                break
    exhaustive = checked == 2 ** (n * n)
    status = UNSAT if count == 0 else UNIQUE if count == 1 else MULTIPLE
    return CheckResult(
        checked, count, status, first_model if count == 1 and exhaustive else None,
        exhaustive, perf_counter() - started, classifications=_classifications(seen, exhaustive),
    )


def check_public_kb(public_kb: PublicKB, *, stop_after_two: bool = False) -> CheckResult:
    """Check only revealed clues and proved verdicts from PublicKB, without hidden labels.

    Exhaustive classifications provide an independent reference for agent tests.
    Incomplete search returns classifications=None. Invalid proved statuses raise
    ValueError instead of silently converting UNKNOWN or malformed data to Innocent.
    """
    if not isinstance(public_kb, PublicKB) or not isinstance(public_kb.proved, Mapping):
        raise ValueError("Expected PublicKB with a mapping of proved verdicts")
    if any(status not in STATUSES for status in public_kb.proved.values()):
        raise ValueError("Proved verdicts must be CRIMINAL or INNOCENT")
    known = {cell: status == CRIMINAL for cell, status in public_kb.proved.items()}
    return count_solutions(public_kb.revealed_clues, public_kb.n,
                           known_statuses=known, stop_after_two=stop_after_two)


def _puzzle_clues(puzzle: dict, n: int) -> tuple[list[Clue], Assignment, Assignment]:
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
        clues.append(clue_from_dict(cell, raw))
        labels[cell], names[cell] = character["criminal"], character["name"].casefold()
    ordered_names = [names[cell] for cell in board.all_cells(n)]
    if any(a >= b for a, b in zip(ordered_names, ordered_names[1:])):
        raise ValueError("Character names must be distinct and alphabetical in row-major order")
    revealed = puzzle.get("initially_revealed")
    if not isinstance(revealed, list) or not revealed:
        raise ValueError("initially_revealed must be a nonempty list")
    for cell in revealed:
        _validate_cell(cell, n)
    if len(set(revealed)) != len(revealed):
        raise ValueError("Duplicate initially revealed cell")
    return clues, {cell: labels[cell] for cell in revealed}, labels


def check_puzzle(puzzle: dict, *, stop_after_two: bool = False) -> CheckResult:
    """Check all clues plus initially face-up statuses in a JSON-format puzzle.

    Face-down criminal labels are schema-validated but NEVER constrain the search.
    After solving, compares all stored labels to the unique model (when available).
    Does not mutate input; that comparison never changes the search or its count.
    Invalid input raises ValueError; UNSAT and MULTIPLE are legitimate check results.
    """
    started = perf_counter()
    if not isinstance(puzzle, dict):
        raise ValueError("Puzzle must be an object")
    n = puzzle.get("n")
    _validate_size(n)
    clues, known, labels = _puzzle_clues(puzzle, n)
    result = count_solutions(clues, n, known_statuses=known, stop_after_two=stop_after_two)
    match = labels == result.unique_solution if result.unique_solution is not None else None
    return replace(result, labels_match_solution=match, runtime=perf_counter() - started)


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
        detail = str(error) or "No further error details"
        if isinstance(error, NotImplementedError):
            detail = str(error) or (
                "semantic.evaluate is unimplemented; D5/D6 integration is required"
            )
        parser.exit(2, f"Checker error ({type(error).__name__}): {detail}\n")
    print(json.dumps({**asdict(result), "count_is_exact": result.count_is_exact}, indent=2))
    if result.labels_match_solution is False:
        parser.exit(1, "Stored labels do not match the unique solution\n")


if __name__ == "__main__":
    main()
