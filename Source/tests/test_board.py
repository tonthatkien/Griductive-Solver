import unittest

from engine import board


class TestBoard(unittest.TestCase):
    def test_neighbors_of_corner_has_three_cells(self):
        self.assertEqual(sorted(board.neighbor_cells(3, "A1")), ["A2", "B1", "B2"])

    def test_neighbors_of_center_has_eight_cells(self):
        self.assertEqual(len(board.neighbor_cells(3, "B2")), 8)

    def test_var_mapping_round_trip(self):
        for cell in board.all_cells(4):
            self.assertEqual(board.cell_of_var(board.var_of(cell, 4), 4), cell)

    def test_row_major_order(self):
        self.assertEqual(board.all_cells(2), ["A1", "B1", "A2", "B2"])


if __name__ == "__main__":
    unittest.main()
