"""Command line: `parts-db validate`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .validate import cold_root_from_env, validate

REPO_ROOT = Path(__file__).resolve().parents[2]


def _cmd_validate(args: argparse.Namespace) -> int:
    cold_root = None
    if args.cold:
        cold_root = cold_root_from_env()
        if cold_root is None:
            print("--cold needs PCB_COLD_STORAGE set (see .env.example); skipping the cold storage check")
    report = validate(Path(args.data), cold_root)
    print(", ".join(f"{n} {k}" for k, n in report.counts.items()))
    for note in report.notes:
        print(note)
    if report.ok:
        print("OK")
        return 0
    print(f"{len(report.errors)} error(s):")
    for e in report.errors:
        print(f"  {e}")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="parts-db", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("validate", help="check the data files")
    p.add_argument("--data", default=str(REPO_ROOT / "data"), help="data folder (default: the repo's data/)")
    p.add_argument("--cold", action="store_true", help="also check each document's PDF in cold storage")
    p.set_defaults(func=_cmd_validate)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
