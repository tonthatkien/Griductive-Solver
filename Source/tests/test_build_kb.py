"""Test C6: Encoder.build_kb = CNF(clue đã lật) ∧ unit clause của ô đã chứng minh."""
import unittest
from copy import deepcopy
from pathlib import Path

from engine.clue import Clue
from engine.constants import CRIMINAL, INCONSISTENT, INNOCENT, UNKNOWN
from engine.game_state import GameEngine, PublicKB
from logic.cnf_encoder import Encoder
from logic.dpll import DPLLSolver

P01_PATH = Path(__file__).resolve().parents[1] / "data" / "puzzles_3x3" / "p01.json"
N = 3
ROW1 = {"type": "row", "number": 1}


def p01_public_kb() -> PublicKB:
    engine = GameEngine()
    engine.load_puzzle(P01_PATH)
    return engine.get_public_kb()


def parity_clue(owner: str) -> Clue:
    return Clue(id=f"clue_{owner}", owner=owner, type="PARITY",
                params={"region": ROW1, "parity": "ODD"})


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
        bad = Clue(id="clue_A1", owner="A1", type="FACT", params={"target": "D1",
                                                                  "status": CRIMINAL})
        with self.assertRaises(ValueError):
            Encoder(N).build_kb(PublicKB(N, revealed_clues=(bad,)))


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


if __name__ == "__main__":
    unittest.main()
