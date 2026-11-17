"""Random walks: blind spot checks of records against their source pages.

`pick` chooses records at random, weighted toward weak trust and records walked less often, and
writes blind tasks: the citation and the shape of the value (a template with every value blanked),
never the value itself. A walker agent (Sonnet) fills the templates from the PDFs. `score` compares
the walker's values with ours and writes a walk log for data/walks/. Logs are reviews: agreement can
promote trust (CLAUDE.md truth rule 4), disagreement becomes a conflict. The curator does both.

Draft (David, 2026-11-17): expect the task shape to change as the data grows.
"""

from __future__ import annotations

import math
import random
import re
from pathlib import Path

import yaml

from .validate import TRUST_LEVELS, cold_root_from_env

# Pick weight by trust: weaker records get walked more often.
TRUST_WEIGHT = {"extracted": 8, "cross-checked": 4, "simulated": 2, "human-reviewed": 1, "proven-on-hardware": 0.5}
GAP_WEIGHT = 3
DOC_ID_RE = re.compile(r"\b[0-9a-f]{16}\b")
SELECTOR_KEYS = {"applies_to"}  # given to the walker as part of the question
META_KEYS = {"trust"}  # ours, not the source's; dropped from templates
VERDICTS = {"agree", "disagree", "unstated"}


def _load_all(data_dir: Path):
    def load(p):
        return yaml.safe_load(p.read_text(encoding="utf-8"))

    families = {d["family"]: d for d in (load(p) for p in sorted((data_dir / "families").rglob("*.yaml")))}
    parts = {d["part"]: d for d in (load(p) for p in sorted((data_dir / "parts").rglob("*.yaml")))}
    walks = [load(p) for p in sorted((data_dir / "walks").glob("*.yaml"))]
    return families, parts, walks


def _weakest_trust(fact: dict) -> str:
    if fact.get("trust") == "per-row":
        rows = [r.get("trust") for r in fact.get("value") or [] if isinstance(r, dict)]
        return min(rows, key=TRUST_LEVELS.index) if rows else "extracted"
    return fact.get("trust", "extracted")


def _template(value):
    """Our value with every leaf blanked; selectors kept, our metadata dropped."""
    if isinstance(value, dict):
        return {k: (v if k in SELECTOR_KEYS else _template(v)) for k, v in value.items() if k not in META_KEYS}
    if isinstance(value, list):
        return [_template(v) for v in value]
    return None


def candidates(data_dir: Path, subject: str | None = None):
    """(record id, weight, task without its id) for every walkable record."""
    families, parts, walks = _load_all(data_dir)
    walked: dict[str, int] = {}
    for log in walks:
        for r in log.get("results") or []:
            walked[r["record"]] = walked.get(r["record"], 0) + 1

    scopes = []  # (label, family record, records holder)
    for part_key, part in parts.items():
        fam = families.get(part.get("family"), {})
        if subject in (None, part_key, part.get("family")):
            scopes.append((part_key, fam, part))
            scopes.append((part_key, fam, fam))
    out, seen = [], set()
    for label, fam, holder in scopes:
        for fact in holder.get("facts") or []:
            src = fact.get("source") or {}
            if fact.get("id") in seen or fact.get("status") != "active" or "doc" not in src:
                continue  # derived facts are recomputed by validate; web-only sources have no PDF
            seen.add(fact["id"])
            task = {
                "kind": "fact",
                "subject": f"{fam.get('manufacturer')} {fam.get('series')} ({label})",
                "key": fact["key"],
                "conditions": fact.get("conditions"),
                "unit": fact.get("unit"),
                "template": _template(fact["value"]),
                "cite": {"doc": src["doc"], "page": src.get("page"), "where": src.get("where")},
            }
            w = TRUST_WEIGHT[_weakest_trust(fact)] / (1 + walked.get(fact["id"], 0))
            out.append((fact["id"], w, task))
        for gap in holder.get("gaps") or []:
            docs = sorted({d for s in gap.get("searched") or [] for d in DOC_ID_RE.findall(str(s.get("where")))})
            if gap.get("id") in seen or gap.get("status") != "open" or not docs:
                continue  # a gap with no searched documents has nothing to re-read
            seen.add(gap["id"])
            task = {
                "kind": "gap",
                "subject": f"{fam.get('manufacturer')} {fam.get('series')} ({label})",
                "key": gap["key"],
                "question": gap["question"],
                "docs": docs,
                "template": {"found": None, "value": None, "page": None},
            }
            out.append((gap["id"], GAP_WEIGHT / (1 + walked.get(gap["id"], 0)), task))
    return out


def pick(data_dir: Path, n: int, seed: int, subject: str | None = None) -> tuple[dict, dict]:
    """Weighted pick without replacement. Returns (blind tasks, key mapping task -> record id)."""
    rng = random.Random(seed)
    pool = candidates(data_dir, subject)
    chosen = []
    while pool and len(chosen) < n:
        total = sum(w for _, w, _ in pool)
        x = rng.uniform(0, total)
        for i, (_, w, _) in enumerate(pool):
            x -= w
            if x <= 0:
                break
        chosen.append(pool.pop(i))
    cold = cold_root_from_env()
    tasks, key = [], {}
    for i, (rid, _, task) in enumerate(chosen, 1):
        tid = f"t{i}"
        key[tid] = rid
        docs = [task["cite"]["doc"]] if task["kind"] == "fact" else task["docs"]
        if cold is not None:
            task["pdfs"] = {d: str(_pdf_for(data_dir, cold, d)) for d in docs}
        tasks.append({"task": tid, **task})
    return {"seed": seed, "subject": subject, "tasks": tasks}, {"seed": seed, "records": key}


def _pdf_for(data_dir: Path, cold: Path, doc: str) -> Path:
    d = yaml.safe_load((data_dir / "documents" / f"{doc}.yaml").read_text(encoding="utf-8"))
    return cold / d["cold_storage"]


def _norm(x):
    if isinstance(x, bool):
        return x
    try:
        return float(x)
    except (TypeError, ValueError):
        return re.sub(r"\s+", "", str(x)).lower() if x is not None else None


def _same(a, b) -> bool:
    a, b = _norm(a), _norm(b)
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-9)
    return a == b


def _diff(ours, theirs, path="value", out=None):
    """Leaf-by-leaf differences, skipping selectors and our metadata."""
    out = [] if out is None else out
    if isinstance(ours, dict):
        theirs = theirs if isinstance(theirs, dict) else {}
        for k, v in ours.items():
            if k not in SELECTOR_KEYS and k not in META_KEYS:
                _diff(v, theirs.get(k), f"{path}.{k}", out)
    elif isinstance(ours, list):
        theirs = theirs if isinstance(theirs, list) else []
        for i, v in enumerate(ours):
            _diff(v, theirs[i] if i < len(theirs) else None, f"{path}[{i}]", out)
    elif not _same(ours, theirs):
        out.append({"path": path, "ours": ours, "walker": theirs})
    return out


def score(data_dir: Path, key: dict, results: dict, date: str, walker: str) -> dict:
    families, parts, _ = _load_all(data_dir)
    facts, gaps = {}, {}
    for holder in [*families.values(), *parts.values()]:
        facts.update({f["id"]: f for f in holder.get("facts") or []})
        gaps.update({g["id"]: g for g in holder.get("gaps") or []})
    by_task = {r["task"]: r for r in results.get("results") or []}
    out = []
    for tid, rid in key["records"].items():
        r = by_task.get(tid)
        entry = {"record": rid}
        if r is None:
            entry.update(verdict="unstated", note="walker returned nothing for this task")
        elif rid in gaps:
            found = bool((r.get("value") or {}).get("found"))
            entry["verdict"] = "disagree" if found else "agree"
            if found:
                entry["walker"] = r["value"]
        elif r.get("value") is None:
            entry.update(verdict="unstated", note=r.get("note") or "walker found no value at the cited place")
        else:
            fact = facts[rid]
            diffs = _diff(fact["value"], r["value"])
            entry["verdict"] = "disagree" if diffs else "agree"
            if diffs:
                entry["diffs"] = diffs
            if fact.get("trust") == "per-row":
                bad = {int(re.match(r"value\[(\d+)\]", d["path"]).group(1)) for d in diffs}
                entry["rows_agreed"] = [i for i in range(len(fact["value"])) if i not in bad]
        if r and r.get("note"):
            entry.setdefault("note", r["note"])
        out.append(entry)
    return {"schema_version": 0, "date": date, "seed": key["seed"], "walker": walker, "results": out}
