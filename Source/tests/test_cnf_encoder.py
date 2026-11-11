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

    def test_literal_of_default_status_is_criminal(self):
        self.assertEqual(Encoder(3).literal_of("A1"), 1)

    def test_literal_of_invalid_status_raises(self):
        with self.assertRaises(ValueError):
            Encoder(3).literal_of("A1", "UNKNOWN")

    def test_kb_counts(self):
        kb = KB(clauses=[[1, -2], [3]], num_primary=9, num_aux=2)
        self.assertEqual(kb.num_vars, 11)
        self.assertEqual(kb.num_clauses, 2)

    def test_num_primary_is_n_squared(self):
        self.assertEqual(Encoder(3).num_primary, 9)
        self.assertEqual(Encoder(5).num_primary, 25)


if __name__ == "__main__":
    unittest.main()
