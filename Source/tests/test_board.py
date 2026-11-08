import unittest

from engine import board


class TestBoard(unittest.TestCase):
    # --- Các test đã có sẵn[cite: 1] ---
    def test_neighbors_of_corner_has_three_cells(self):
        self.assertEqual(sorted(board.neighbor_cells(3, "A1")), ["A2", "B1", "B2"])

    def test_neighbors_of_center_has_eight_cells(self):
        self.assertEqual(len(board.neighbor_cells(3, "B2")), 8)

    def test_var_mapping_round_trip(self):
        for cell in board.all_cells(4):
            self.assertEqual(board.cell_of_var(board.var_of(cell, 4), 4), cell)

    def test_row_major_order(self):
        self.assertEqual(board.all_cells(2), ["A1", "B1", "A2", "B2"])

    # --- Các test bổ sung cho Task A1 ---
    def test_neighbors_edge_and_order(self):
        # Neighbor ở biên có 5 ô
        self.assertEqual(len(board.neighbor_cells(3, "B1")), 5)
        # Neighbor không chứa chính nó và đúng thứ tự row-major
        self.assertEqual(
            board.neighbor_cells(3, "B2"),
            ["A1", "B1", "C1", "A2", "C2", "A3", "B3", "C3"]
        )

    def test_neighbors_1x1_empty(self):
        self.assertEqual(board.neighbor_cells(1, "A1"), [])

    def test_var_of_values(self):
        self.assertEqual(board.var_of("A1", 3), 1)
        self.assertEqual(board.var_of("C2", 3), 6)
        self.assertEqual(board.var_of("C3", 3), 9)

    def test_parse_and_cell_id_inverse(self):
        self.assertEqual(board.parse_cell("C2"), (1, 2))
        self.assertEqual(board.cell_id(1, 2), "C2")

    def test_row_and_col_cells(self):
        self.assertEqual(board.row_cells(3, 2), ["A2", "B2", "C2"])
        self.assertEqual(board.col_cells(3, "B"), ["B1", "B2", "B3"])

    def test_is_valid_cell(self):
        self.assertTrue(board.is_valid_cell("A1", 3))
        self.assertFalse(board.is_valid_cell("D1", 3))
        self.assertFalse(board.is_valid_cell("A0", 3))
        self.assertFalse(board.is_valid_cell("A", 3))
        self.assertFalse(board.is_valid_cell("", 3))

    def test_cell_of_var_invalid(self):
        with self.assertRaises(ValueError):
            board.cell_of_var(0, 3)
        with self.assertRaises(ValueError):
            board.cell_of_var(10, 3)

    def test_invalid_cells_raise_value_error(self):
        with self.assertRaises(ValueError):
            board.neighbor_cells(3, "D1")
        with self.assertRaises(ValueError):
            board.var_of("Z9", 3)

    def test_first_aux_var(self):
        self.assertEqual(board.first_aux_var(3), 10)


if __name__ == "__main__":
    unittest.main()