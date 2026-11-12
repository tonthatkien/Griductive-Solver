"""Entry point: chạy GUI.

  python main.py                                   # mở GUI, hỏi chọn file puzzle
  python main.py --puzzle data/puzzles_3x3/p01.json
  python main.py --demo                            # backend GIẢ để xem giao diện (xóa trước khi nộp)
"""
import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Griductive Solver")
    parser.add_argument("--puzzle", default=None, help="đường dẫn file puzzle .json")
    parser.add_argument("--demo", action="store_true",
                        help="dùng engine/agent giả (gui/demo_backend.py) khi code thật chưa xong")
    args = parser.parse_args()
    from gui.app import run
    return run(args.puzzle, args.demo)


if __name__ == "__main__":
    sys.exit(main())
