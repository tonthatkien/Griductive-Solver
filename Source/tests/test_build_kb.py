"""Test C6: Encoder.build_kb = CNF(clue đã lật) ∧ unit clause của ô đã chứng minh."""
import json
import random
import unittest
from copy import deepcopy
from pathlib import Path

from engine import board
from engine.clue import Clue, clue_from_dict
from engine.constants import CRIMINAL, INCONSISTENT, INNOCENT, UNKNOWN
from engine.game_state import GameEngine, PublicKB
from logic.cnf_encoder import Encoder
from logic.dpll import DPLLSolver
from logic.semantic import evaluate

P01_PATH = Path(__file__).resolve().parents[1] / "data" / "puzzles_3x3" / "p01.json"
N = 3
ROW1 = {"type": "row", "number": 1}
COLA = {"type": "col", "letter": "A"}


def p01_public_kb() -> PublicKB:
    engine = GameEngine()
    engine.load_puzzle(P01_PATH)
    return engine.get_public_kb()


def parity_clue(owner: str) -> Clue:
    return Clue(id=f"clue_{owner}", owner=owner, type="PARITY",
                params={"region": ROW1, "parity": "ODD"})


def compare_clue(owner: str) -> Clue:
    return Clue(id=f"clue_{owner}", owner=owner, type="COMPARE",
                params={"region1": ROW1, "region2": COLA, "op": "GT"})


def fact_clue(owner: str) -> Clue:
    return Clue(id=f"clue_{owner}", owner=owner, type="FACT",
                params={"target": "B2", "status": CRIMINAL})


def same_clue(owner: str) -> Clue:
    return Clue(id=f"clue_{owner}", owner=owner, type="SAME_STATUS",
                params={"cell1": "A1", "cell2": "C2"})


def mixed_public_kb() -> PublicKB:
    """FACT + PARITY + COMPARE + SAME: 13 biến phụ (1 của PARITY, 12 của COMPARE)."""
    return PublicKB(N, revealed_clues=(fact_clue("A1"), parity_clue("B1"),
                                       compare_clue("C1"), same_clue("A2")),
                    proved={"A1": CRIMINAL})


class TestBuildKbContent(unittest.TestCase):
    def test_empty_public_kb_gives_empty_kb(self):
        kb = Encoder(N).build_kb(PublicKB(N))
        self.assertEqual(kb.clauses, [])
        self.assertEqual((kb.num_primary, kb.num_aux, kb.num_clauses), (9, 0, 0))

    def test_p01_initial_kb_exact_clauses(self):
        # A1: FACT B2 criminal; C1: EXACTLY 2 criminal ở cột C (vars 3, 6, 9);
        # proved: A1 criminal, C1 innocent
        kb = Encoder(N).build_kb(p01_public_kb())
        self.assertEqual(kb.clauses, [
            [5],
            [-3, -6, -9], [3, 6], [3, 9], [6, 9],
            [1], [-3],
        ])
        self.assertEqual((kb.num_primary, kb.num_aux, kb.num_vars), (9, 0, 9))

    def test_proved_units_follow_row_major_and_status_polarity(self):
        kb = Encoder(N).build_kb(PublicKB(N, proved={"C3": CRIMINAL, "A1": INNOCENT}))
        self.assertEqual(kb.clauses, [[-1], [9]])

    def test_only_public_data_is_encoded(self):
        public = p01_public_kb()
        kb = Encoder(N).build_kb(public)
        unit_vars = {abs(c[0]) for c in kb.clauses if len(c) == 1}
        # unit clause chỉ có FACT B2 (var 5) và hai ô đã chứng minh A1, C1 (var 1, 3)
        self.assertEqual(unit_vars, {1, 3, 5})
        self.assertEqual(sorted(public.proved), ["A1", "C1"])

    def test_does_not_mutate_public_kb(self):
        public = p01_public_kb()
        before = deepcopy(public)
        Encoder(N).build_kb(public)
        self.assertEqual(public, before)

    def test_build_is_deterministic(self):
        public = p01_public_kb()
        self.assertEqual(Encoder(N).build_kb(public).clauses, Encoder(N).build_kb(public).clauses)


class TestBuildKbAuxVars(unittest.TestCase):
    def test_aux_vars_counted_and_start_after_primary(self):
        public = PublicKB(N, revealed_clues=[parity_clue("A1"), parity_clue("B1")])
        kb = Encoder(N).build_kb(public)
        self.assertEqual(kb.num_aux, 2)  # mỗi PARITY trên hàng 3 ô: 1 biến phụ
        self.assertEqual(kb.num_vars, 11)
        used = {abs(lit) for clause in kb.clauses for lit in clause}
        self.assertEqual({v for v in used if v > 9}, {10, 11})

    def test_reused_encoder_does_not_accumulate_aux(self):
        public = PublicKB(N, revealed_clues=[parity_clue("A1")])
        enc = Encoder(N)
        first = enc.build_kb(public)
        second = enc.build_kb(public)
        self.assertEqual(first.clauses, second.clauses)
        self.assertEqual((first.num_aux, second.num_aux), (1, 1))
        self.assertEqual(enc.new_aux(), 11)  # sau build, bộ đếm tiếp tục từ biến phụ cuối


class TestBuildKbInvalidInput(unittest.TestCase):
    def test_grid_size_mismatch_raises(self):
        with self.assertRaises(ValueError):
            Encoder(4).build_kb(PublicKB(3))

    def test_invalid_proved_cell_raises(self):
        for bad in ("D1", "a1", "A0", ""):
            with self.subTest(cell=bad), self.assertRaises(ValueError):
                Encoder(N).build_kb(PublicKB(N, proved={bad: CRIMINAL}))

    def test_invalid_proved_verdict_raises(self):
        for bad in (UNKNOWN, INCONSISTENT, "criminal", None):
            with self.subTest(verdict=bad), self.assertRaises(ValueError):
                Encoder(N).build_kb(PublicKB(N, proved={"A1": bad}))

    def test_invalid_revealed_clue_raises(self):
        bad = Clue(id="clue_A1", owner="A1", type="FACT",
                   params={"target": "D1", "status": CRIMINAL})
        with self.assertRaises(ValueError):
            Encoder(N).build_kb(PublicKB(N, revealed_clues=[bad]))


class TestBuildKbWithDpll(unittest.TestCase):
    """Tích hợp nhẹ: KB của p01 lúc đầu suy ra đúng đợt đầu (B2, C2, C3), A3 chưa."""

    def test_p01_first_wave_entailment(self):
        kb = Encoder(N).build_kb(p01_public_kb())
        solver = DPLLSolver()
        self.assertTrue(solver.solve(kb.clauses, kb.num_vars).sat)
        for var in (5, 6, 9):  # B2, C2, C3
            with self.subTest(var=var):
                self.assertFalse(solver.solve(kb.clauses, kb.num_vars, assumptions=[-var]).sat)
        for lit in (7, -7):  # A3 còn UNKNOWN
            with self.subTest(lit=lit):
                self.assertTrue(solver.solve(kb.clauses, kb.num_vars, assumptions=[lit]).sat)

    def test_proved_contradicting_revealed_clue_makes_kb_unsat(self):
        fact_b2 = Clue(id="clue_A1", owner="A1", type="FACT",
                       params={"target": "B2", "status": CRIMINAL})
        public = PublicKB(N, revealed_clues=[fact_b2], proved={"B2": INNOCENT})
        kb = Encoder(N).build_kb(public)
        self.assertEqual(kb.clauses, [[5], [-5]])
        result = DPLLSolver().solve(kb.clauses, kb.num_vars)
        self.assertFalse(result.sat)
        self.assertFalse(result.timed_out)


class TestBuildKbFullPuzzle(unittest.TestCase):
    """Dùng TOÀN BỘ clue của p01 (chỉ trong test, agent không bao giờ làm vậy).

    p01 là puzzle có nghiệm duy nhất, nên KB dựng từ toàn bộ clue của nó phải có
    đúng một model trên biến primary, và model đó khớp nhãn ẩn. Đây là kiểm tra
    cho riêng p01, không phải kiểm tra tổng quát cho mọi puzzle."""

    def test_p01_all_clues_give_unique_model_matching_labels(self):
        with P01_PATH.open(encoding="utf-8") as fh:
            data = json.load(fh)
        chars = sorted(data["characters"], key=lambda c: board.cell_index(c["cell"], N))
        labels = {c["cell"]: c["criminal"] for c in chars}
        clues = [clue_from_dict(c["cell"], c["clue"]) for c in chars]
        proved = {cell: CRIMINAL if labels[cell] else INNOCENT
                  for cell in data["initially_revealed"]}
        kb = Encoder(N).build_kb(PublicKB(N, revealed_clues=clues, proved=proved))

        solver = DPLLSolver()
        result = solver.solve(kb.clauses, kb.num_vars)
        self.assertTrue(result.sat)
        primary = range(1, kb.num_primary + 1)
        expected = {board.var_of(cell, N): value for cell, value in labels.items()}
        self.assertEqual({v: result.model[v] for v in primary}, expected)

        # blocking clause chỉ trên biến primary: không còn nghiệm thứ hai
        block = [-v if result.model[v] else v for v in primary]
        self.assertFalse(solver.solve(kb.clauses + [block], kb.num_vars).sat)


class TestBuildKbMixedEncodings(unittest.TestCase):
    def test_aux_vars_are_disjoint_across_encodings(self):
        public = mixed_public_kb()
        kb = Encoder(N).build_kb(public)
        self.assertEqual(kb.num_aux, 13)
        used = {abs(lit) for clause in kb.clauses for lit in clause}
        self.assertEqual({v for v in used if v > 9}, set(range(10, 23)))

    def test_kb_matches_semantic_on_sampled_assignments(self):
        public = mixed_public_kb()
        kb = Encoder(N).build_kb(public)
        solver = DPLLSolver()
        rng = random.Random(2026)
        cells = board.all_cells(N)
        # Mẫu thỏa chắc chắn: A1, B1, C1, B2, C2 criminal; còn lại innocent
        satisfying = {c: c in ("A1", "B1", "C1", "B2", "C2") for c in cells}
        samples = [satisfying] + [{c: rng.random() < 0.5 for c in cells} for _ in range(80)]
        sat_seen = unsat_seen = 0
        for assignment in samples:
            assumptions = [board.var_of(c, N) if v else -board.var_of(c, N)
                           for c, v in assignment.items()]
            expected = assignment["A1"] and all(
                evaluate(clue, assignment, N) for clue in public.revealed_clues)
            with self.subTest(assignment=assignment):
                result = solver.solve(kb.clauses, kb.num_vars, assumptions=assumptions)
                self.assertEqual(result.sat, expected)
            sat_seen += expected
            unsat_seen += not expected
        self.assertGreater(sat_seen, 0)
        self.assertGreater(unsat_seen, 0)


class TestBuildKbLifecycle(unittest.TestCase):
    def test_reuse_with_changing_public_kb(self):
        heavy = mixed_public_kb()
        light = PublicKB(N, revealed_clues=(fact_clue("A1"), same_clue("B1")))
        enc = Encoder(N)
        first, second, third = enc.build_kb(heavy), enc.build_kb(light), enc.build_kb(heavy)
        self.assertEqual((first.num_aux, second.num_aux, third.num_aux), (13, 0, 13))
        self.assertEqual(second.num_vars, 9)
        self.assertEqual(second.clauses, Encoder(N).build_kb(light).clauses)
        self.assertEqual(third.clauses, first.clauses)
        self.assertEqual(enc.new_aux(), 23)

    def test_failed_build_does_not_affect_next_build(self):
        good = mixed_public_kb()
        expected = Encoder(N).build_kb(good)
        bad_clue = Clue(id="clue_C2", owner="C2", type="FACT",
                        params={"target": "D1", "status": CRIMINAL})
        bad_cases = {
            "invalid_clue_after_aux": PublicKB(N, revealed_clues=(parity_clue("A1"), bad_clue)),
            "invalid_verdict_after_aux": PublicKB(N, revealed_clues=(parity_clue("A1"),),
                                                  proved={"A1": UNKNOWN}),
        }
        for name, bad in bad_cases.items():
            with self.subTest(case=name):
                enc = Encoder(N)
                with self.assertRaises(ValueError):
                    enc.build_kb(bad)
                after = enc.build_kb(good)
                self.assertEqual(after.clauses, expected.clauses)
                self.assertEqual(after.num_aux, expected.num_aux)


if __name__ == "__main__":
    unittest.main()
