import unittest

from logic.cnf_encoder import KB, Encoder


class TestEncoderBase(unittest.TestCase):
    def test_first_aux_var_follows_primary_vars(self):
        self.assertEqual(Encoder(3).new_aux(), 10)
        self.assertEqual(Encoder(4).new_aux(), 17)

    def test_new_aux_increments_and_counts(self):
        enc = Encoder(3)
        self.assertEqual([enc.new_aux(), enc.new_aux(), enc.new_aux()], [10, 11, 12])
        self.assertEqual(enc.num_aux, 3)

    def test_literal_of_criminal_is_positive(self):
        self.assertEqual(Encoder(3).literal_of("C2", "CRIMINAL"), 6)

    def test_literal_of_innocent_is_negative(self):
        self.assertEqual(Encoder(3).literal_of("C2", "INNOCENT"), -6)

    def test_literal_of_requires_status(self):
        with self.assertRaises(TypeError):
            Encoder(3).literal_of("A1")

    def test_literal_of_invalid_cell_raises(self):
        for bad in ["D1", "a1", "A0", "A01", ""]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                Encoder(3).literal_of(bad, "CRIMINAL")

    def test_literal_of_bad_status_raises(self):
        for bad in ["criminal", "UNKNOWN", None]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                Encoder(3).literal_of("A1", bad)

    def test_literal_of_asymmetric_cell_catches_row_col_swap(self):
        self.assertEqual(Encoder(4).literal_of("B3", "CRIMINAL"), 10)
        self.assertEqual(Encoder(4).literal_of("B3", "INNOCENT"), -10)

    def test_two_encoders_have_independent_aux_counters(self):
        e1, e2 = Encoder(3), Encoder(3)
        e1.new_aux()
        self.assertEqual(e2.new_aux(), 10)
        self.assertEqual(e1.new_aux(), 11)

    def test_new_aux_does_not_change_num_primary(self):
        enc = Encoder(3)
        enc.new_aux()
        self.assertEqual(enc.num_primary, 9)

    def test_empty_kb_has_zero_clauses(self):
        kb = KB(clauses=[], num_primary=9, num_aux=0)
        self.assertEqual(kb.num_clauses, 0)
        self.assertEqual(kb.num_vars, 9)

    def test_kb_counts(self):
        kb = KB(clauses=[[1, -2], [3]], num_primary=9, num_aux=2)
        self.assertEqual(kb.num_vars, 11)
        self.assertEqual(kb.num_clauses, 2)

    def test_num_primary_is_n_squared(self):
        self.assertEqual(Encoder(3).num_primary, 9)
        self.assertEqual(Encoder(5).num_primary, 25)


if __name__ == "__main__":
    unittest.main()
