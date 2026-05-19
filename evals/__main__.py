"""CLI entry: run with `uv run python -m evals`."""

import sys
from .runner import run, print_report


def main() -> int:
    report = run()
    print_report(report)
    return 0 if report.pass_count == report.total else 1


if __name__ == "__main__":
    sys.exit(main())
