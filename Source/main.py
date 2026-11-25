"""Entry point: chạy GUI.

  python main.py                                   # mở bản đồ vụ án, bấm địa điểm để chọn màn
  python main.py --puzzle data/puzzles_3x3/p01.json   # vào thẳng màn chơi, bỏ qua bản đồ
"""
import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Griductive Solver")
    parser.add_argument("--puzzle", default=None, help="đường dẫn file puzzle .json")
    args = parser.parse_args()
    from gui.app import run
    return run(args.puzzle)


if __name__ == "__main__":
    sys.exit(main())
