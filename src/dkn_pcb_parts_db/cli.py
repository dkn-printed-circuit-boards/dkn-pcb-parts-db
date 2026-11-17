"""Command line: `parts-db validate` and `parts-db lookup`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

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


def _cmd_lookup(args: argparse.Namespace) -> int:
    """Exit 0: current answer. 1: not cached. 2: stale. 3: the data does not validate."""
    report = validate(Path(args.data))
    if not report.ok:
        print(f"data has {len(report.errors)} error(s); run `parts-db validate` first")
        return 3
    hits = [a for a in report.answers
            if a["_subject"] == args.subject and a.get("key") == args.key and a.get("status") == "active"]
    if not hits:
        print(f"not cached: {args.subject} {args.key}")
        return 1
    worst = 0
    for ans in hits:
        shown = {k: v for k, v in ans.items() if not k.startswith("_")}
        print(yaml.safe_dump(shown, sort_keys=False, allow_unicode=True).rstrip())
        reasons = report.stale.get(ans["id"])
        if reasons:
            worst = 2
            print("STALE:")
            for r in reasons:
                print(f"  - {r}")
        else:
            print("CURRENT")
        print()
    return worst


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="parts-db", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("validate", help="check the data files")
    p.add_argument("--data", default=str(REPO_ROOT / "data"), help="data folder (default: the repo's data/)")
    p.add_argument("--cold", action="store_true", help="also check each document's PDF in cold storage")
    p.set_defaults(func=_cmd_validate)
    q = sub.add_parser("lookup", help="find a cached answer and say whether it is still current")
    q.add_argument("subject", help="part key <maker>:<MPN> or family id, e.g. rohm:ESR03EZPF1002")
    q.add_argument("key", help="fact key, e.g. power.rated")
    q.add_argument("--data", default=str(REPO_ROOT / "data"), help="data folder (default: the repo's data/)")
    q.set_defaults(func=_cmd_lookup)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
