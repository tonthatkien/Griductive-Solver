"""Entry point: chạy GUI.

TODO(Scope F): parse argument (--puzzle), tạo GameEngine, tạo Agent, mở gui.app.run(...)
"""
import argparse


def main():
    parser = argparse.ArgumentParser(description="Griductive Solver")
    parser.add_argument("--puzzle", default=None, help="đường dẫn file puzzle .json")
    args = parser.parse_args()
    from gui.app import run
    run(args.puzzle)


if __name__ == "__main__":
    main()
