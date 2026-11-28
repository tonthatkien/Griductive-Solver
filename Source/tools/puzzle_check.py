"""B6 offline audit: full clues, independent semantic counts and public gameplay."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from engine import board
from engine.clue import Clue, clue_cells, clue_from_dict
from engine.constants import INCONSISTENT
from engine.game_state import GameEngine
from logic.agent import SOLVED, STUCK, LogicAgent, uniqueness_check
from logic.semantic import evaluate
from tools.brute_force import count_solutions

DATA = Path(__file__).resolve().parents[1] / "data"
DEMO_EXPECTATIONS = {
    "ambiguous.json": (STUCK, 256),
    "inconsistent.json": (INCONSISTENT, 0),
}


def puzzle_digest(path: Path) -> str:
    """Hash file content with CRLF normalized to LF for portable checkouts."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _evaluate_checked(clue: Clue, assignment: dict[str, bool], n: int) -> bool:
    verdict = evaluate(clue, assignment, n)
    if type(verdict) is not bool:
        raise TypeError(f"Evaluator must return bool for {clue.id}, got {type(verdict).__name__}")
    return verdict


def semantic_count(clues: tuple[Clue, ...], n: int) -> int:
    """Count exactly by Boolean enumeration; prune only fully evaluated false clues.

    Independent of CNF/DPLL. Each rejected partial assignment stands for all its
    impossible completions. Worst case remains 2**(n*n), never a capped count.
    Intended for validated audit inputs, including 5x5; no hidden labels used.
    """
    cells = board.all_cells(n)
    ready: list[list[Clue]] = [[] for _ in cells]
    order = {cell: i for i, cell in enumerate(cells)}
    for clue in clues:
        # Clue không nhắc ô nào (NOISE) được kiểm ngay ở bước đầu; luôn đúng.
        last = max((order[cell] for cell in clue_cells(clue, n)), default=0)
        ready[last].append(clue)
    smoke = dict.fromkeys(cells, False)
    for clue in clues:
        _evaluate_checked(clue, smoke, n)
    assignment: dict[str, bool] = {}

    def visit(index: int) -> int:
        if index == len(cells):
            return 1
        cell = cells[index]
        total = 0
        for value in (False, True):
            assignment[cell] = value
            if all(_evaluate_checked(clue, assignment, n) for clue in ready[index]):
                total += visit(index + 1)
        del assignment[cell]
        return total

    return visit(0)


def _constraint_result(clues: tuple[Clue, ...], n: int, timeout: float) -> dict:
    unique, capped = uniqueness_check(clues, n, timeout=timeout)
    if n in (3, 4):
        reference = count_solutions(clues, n)
        exact = reference.satisfying_assignments
        method = "B2 exhaustive semantic brute force"
    else:
        exact = semantic_count(clues, n)
        method = "exhaustive semantic enumeration with early false-clue pruning"
    return {
        "dpll_unique": unique, "dpll_count_capped_at_2": capped,
        "semantic_count_exact": exact, "reference_method": method,
        "agreement": capped == min(exact, 2) and unique == (exact == 1),
    }


def audit_puzzle(path: Path, *, timeout: float = 10.0) -> dict:
    """Audit authoring data offline; the playing agent receives only PublicKB."""
    data = json.loads(path.read_text(encoding="utf-8"))
    engine = GameEngine()
    engine.load_puzzle(data)  # Shared schema validation before either checker.
    n = data["n"]
    clues = tuple(clue_from_dict(c["cell"], c["clue"]) for c in data["characters"])
    labels = {c["cell"]: c["criminal"] for c in data["characters"]}
    initial = engine.get_public_kb()
    facts = tuple(clue_from_dict(cell, {
        "type": "FACT", "target": cell, "status": verdict,
    }) for cell, verdict in initial.proved.items())
    pure = _constraint_result(clues, n, timeout)
    with_initial = _constraint_result(clues + facts, n, timeout)
    labels_satisfy = all(evaluate(clue, labels, n) for clue in clues)
    agent = LogicAgent(timeout=timeout)
    entries = agent.auto_solve(engine)
    return {
        "path": path.relative_to(DATA).as_posix(), "n": n,
        "sha256": puzzle_digest(path),
        "clues_only": pure, "clues_plus_initial_facts": with_initial,
        "stored_labels_satisfy_all_clues": labels_satisfy,
        "agent_status": agent.solve_status, "accepted_steps": len(entries),
        "initial_proved": len(initial.proved),
        "final_proved": len(engine.get_public_kb().proved),
    }


def audit_dataset(*, timeout: float = 10.0) -> dict:
    """Audit nine standard puzzles and two explicit intentional failure demos."""
    standard = sorted(DATA.glob("puzzles_*/*.json"))
    demos = sorted((DATA / "demo_cases").glob("*.json"))
    unknown = sorted(path.name for path in demos if path.name not in DEMO_EXPECTATIONS)
    if unknown:
        raise ValueError(f"Missing demo expectation: {', '.join(unknown)}")
    rows = [audit_puzzle(path, timeout=timeout) for path in standard + demos]
    for row in rows:
        name = Path(row["path"]).name
        if row["path"].startswith("demo_cases/"):
            status, count = DEMO_EXPECTATIONS[name]
            row["passes_expectation"] = (
                row["agent_status"] == status and row["accepted_steps"] == 0
                and row["clues_only"]["semantic_count_exact"] == count
                and row["clues_plus_initial_facts"]["semantic_count_exact"] == count
            )
        else:
            row["passes_expectation"] = (
                row["agent_status"] == SOLVED and row["final_proved"] == row["n"] ** 2
                and row["stored_labels_satisfy_all_clues"]
                and row["clues_only"]["semantic_count_exact"] == 1
                and row["clues_plus_initial_facts"]["semantic_count_exact"] == 1
            )
        row["passes_expectation"] &= all(
            row[key]["agreement"] for key in ("clues_only", "clues_plus_initial_facts")
        )
    passed = len(standard) == 9 and {path.name for path in demos} == set(DEMO_EXPECTATIONS) and all(
        row["passes_expectation"] for row in rows
    )
    return {"standard_puzzles": len(standard), "intentional_demos": len(demos),
            "all_passed": passed, "results": rows}


def main() -> int:
    """Print reproducible JSON; nonzero exit on a mismatched expected result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--out", type=Path, help="Write UTF-8 JSON with LF newlines")
    args = parser.parse_args()
    report = audit_dataset(timeout=args.timeout)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(output)
    else:
        print(output, end="")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())