"""Command line: `parts-db validate`, `parts-db lookup`, and `parts-db walk`."""

from __future__ import annotations

import argparse
import datetime
import secrets
import sys
from pathlib import Path

import yaml

from . import walk
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


def _dump(path: Path, d: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _cmd_walk_pick(args: argparse.Namespace) -> int:
    seed = args.seed if args.seed is not None else secrets.randbelow(10**6)
    tasks, key = walk.pick(Path(args.data), args.n, seed, args.subject)
    out = Path(args.out)
    _dump(out / "tasks.yaml", tasks)  # give this to the walker
    _dump(out / "key.yaml", key)  # keep this; it maps tasks to records
    print(f"seed {seed}: {len(tasks['tasks'])} task(s) in {out / 'tasks.yaml'}; key in {out / 'key.yaml'}")
    if not any("pdfs" in t for t in tasks["tasks"]):
        print("PCB_COLD_STORAGE is not set, so the tasks carry no PDF paths")
    return 0


def _cmd_walk_score(args: argparse.Namespace) -> int:
    key = yaml.safe_load(Path(args.key).read_text(encoding="utf-8"))
    results = yaml.safe_load(Path(args.results).read_text(encoding="utf-8"))
    date = args.date or datetime.date.today().isoformat()
    log = walk.score(Path(args.data), key, results, date, args.walker)
    for r in log["results"]:
        print(f"{r['verdict']:9} {r['record']}")
        for d in r.get("diffs") or []:
            print(f"          {d['path']}: ours {d['ours']!r}, walker {d['walker']!r}")
    if args.write:
        path = Path(args.data) / "walks" / f"{date}-s{key['seed']}.yaml"
        _dump(path, log)
        print(f"wrote {path}")
    return 0 if all(r["verdict"] == "agree" for r in log["results"]) else 2


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
    w = sub.add_parser("walk", help="random blind spot checks of records against their PDFs")
    wsub = w.add_subparsers(dest="walk_command", required=True)
    wp = wsub.add_parser("pick", help="pick records and write blind tasks for a walker agent")
    wp.add_argument("--n", type=int, default=5, help="how many records (default 5)")
    wp.add_argument("--seed", type=int, help="random seed (default: a new one, printed)")
    wp.add_argument("--subject", help="only this part key or family id")
    wp.add_argument("--out", required=True, help="folder for tasks.yaml and key.yaml (keep it out of the repo)")
    wp.add_argument("--data", default=str(REPO_ROOT / "data"))
    wp.set_defaults(func=_cmd_walk_pick)
    ws = wsub.add_parser("score", help="compare a walker's results with the records")
    ws.add_argument("key", help="key.yaml from pick")
    ws.add_argument("results", help="the walker's results.yaml")
    ws.add_argument("--walker", required=True, help="who walked and how, e.g. 'Sonnet, blind'")
    ws.add_argument("--date", help="walk date (default today)")
    ws.add_argument("--write", action="store_true", help="save the walk log to data/walks/")
    ws.add_argument("--data", default=str(REPO_ROOT / "data"))
    ws.set_defaults(func=_cmd_walk_score)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
