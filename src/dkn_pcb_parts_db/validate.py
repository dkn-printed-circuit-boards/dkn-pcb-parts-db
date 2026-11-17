"""Check the YAML data files: structure, links between records, and arithmetic.

The text files are the master copy, so this script does the job a database's
constraints would: no dangling citations, no duplicate IDs, known trust levels,
and derived numbers that match their inputs.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

TRUST_LEVELS = ["extracted", "cross-checked", "simulated", "human-reviewed", "proven-on-hardware"]
FACT_STATUS = {"active", "superseded", "disputed"}
RECORD_STATUS = {"open", "resolved"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    def err(self, where: Path | str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    @property
    def ok(self) -> bool:
        return not self.errors


def _load(path: Path, report: Report):
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        report.err(path, f"YAML parse error: {exc}")
        return None
    if not isinstance(data, dict):
        report.err(path, "top level must be a mapping")
        return None
    return data


def _check_trust(where: str, fact: dict, report: Report) -> None:
    trust = fact.get("trust")
    if trust == "per-row":
        rows = fact.get("value")
        if not isinstance(rows, list) or not rows:
            report.err(where, "trust is per-row but value is not a list of rows")
            return
        for i, row in enumerate(rows):
            if not isinstance(row, dict) or row.get("trust") not in TRUST_LEVELS:
                report.err(where, f"row {i}: missing or unknown trust")
    elif trust not in TRUST_LEVELS:
        report.err(where, f"unknown trust {trust!r} (allowed: {', '.join(TRUST_LEVELS)} or per-row)")


def validate(data_dir: Path, cold_root: Path | None = None) -> Report:
    report = Report()
    data_dir = Path(data_dir)
    doc_dir, fam_dir, part_dir = data_dir / "documents", data_dir / "families", data_dir / "parts"

    # --- documents
    docs: dict[str, dict] = {}
    for path in sorted(doc_dir.glob("*.yaml")):
        d = _load(path, report)
        if d is None:
            continue
        sha = str(d.get("sha256", ""))
        if not SHA256_RE.match(sha):
            report.err(path, "sha256 must be 64 lowercase hex characters")
            continue
        if path.stem != sha[:16]:
            report.err(path, f"file name must be the first 16 hex of sha256 ({sha[:16]})")
        for key in ("manufacturer", "title", "type", "url"):
            if not d.get(key):
                report.err(path, f"missing {key}")
        expected_cold = f"datasheets/{sha}.pdf"
        if d.get("cold_storage") != expected_cold:
            report.err(path, f"cold_storage must be {expected_cold}")
        docs[path.stem] = d

    # --- families and parts
    families: dict[str, tuple[Path, dict]] = {}
    for path in sorted(fam_dir.rglob("*.yaml")):
        d = _load(path, report)
        if d is None:
            continue
        for key in ("schema_version", "family", "manufacturer", "category"):
            if key not in d:
                report.err(path, f"missing {key}")
        for doc in d.get("documents") or []:
            if doc not in docs:
                report.err(path, f"lists unknown document {doc}")
        if d.get("family") in families:
            report.err(path, f"duplicate family {d['family']}")
        families[d.get("family")] = (path, d)

    parts: dict[str, tuple[Path, dict]] = {}
    for path in sorted(part_dir.rglob("*.yaml")):
        d = _load(path, report)
        if d is None:
            continue
        for key in ("schema_version", "part", "manufacturer", "mpn", "family"):
            if key not in d:
                report.err(path, f"missing {key}")
        if d.get("part") != f"{d.get('manufacturer')}:{d.get('mpn')}":
            report.err(path, "part must be <manufacturer>:<mpn>")
        if path.stem != d.get("mpn"):
            report.err(path, "file name must be the MPN")
        if d.get("family") not in families:
            report.err(path, f"unknown family {d.get('family')}")
        parts[d.get("part")] = (path, d)

    # --- facts: collect IDs first so links can resolve in any order
    all_facts: dict[str, tuple[Path, dict]] = {}
    record_ids: set[str] = set()
    for path, d in [*families.values(), *parts.values()]:
        for fact in d.get("facts") or []:
            fid = fact.get("id")
            if not fid:
                report.err(path, "fact without id")
                continue
            if fid in all_facts or fid in record_ids:
                report.err(path, f"duplicate id {fid}")
            all_facts[fid] = (path, fact)
        for section in ("conflicts", "gaps"):
            for rec in d.get(section) or []:
                rid = rec.get("id")
                if not rid:
                    report.err(path, f"{section} entry without id")
                elif rid in all_facts or rid in record_ids:
                    report.err(path, f"duplicate id {rid}")
                else:
                    record_ids.add(rid)
                if rec.get("status") not in RECORD_STATUS:
                    report.err(path, f"{rid}: status must be one of {sorted(RECORD_STATUS)}")
        for review in d.get("reviews") or []:
            if not review.get("date") or not review.get("method"):
                report.err(path, "review needs date and method")

    for fid, (path, fact) in all_facts.items():
        where = f"{path} [{fid}]"
        for key in ("key", "value", "status"):
            if key not in fact:
                report.err(where, f"missing {key}")
        _check_trust(where, fact, report)
        if fact.get("status") not in FACT_STATUS:
            report.err(where, f"status must be one of {sorted(FACT_STATUS)}")
        src = fact.get("source") or {}
        if fact.get("method") == "derived":
            if not fact.get("inputs") or not fact.get("derivation"):
                report.err(where, "derived fact needs inputs and derivation")
            for inp in fact.get("inputs") or []:
                if inp not in all_facts:
                    report.err(where, f"unknown input {inp}")
        elif "doc" not in src and "web" not in src:
            report.err(where, "needs a source (doc or web) unless method is derived")
        cites = [src, *(fact.get("also_stated_by") or [])]
        for cite in cites:
            if "doc" in cite and cite["doc"] not in docs:
                report.err(where, f"cites unknown document {cite['doc']}")
            if "doc" in cite and not isinstance(cite.get("page"), int):
                report.err(where, f"citation of {cite['doc']} needs an integer page")
        sup = fact.get("supersedes")
        if sup and sup not in all_facts:
            report.err(where, f"supersedes unknown fact {sup}")

    _check_arithmetic(families, parts, report)

    if cold_root is not None:
        _check_cold(docs, cold_root, report)

    report.counts = {
        "documents": len(docs),
        "families": len(families),
        "parts": len(parts),
        "facts": len(all_facts),
        "conflicts and gaps": len(record_ids),
    }
    return report


def _family_fact(fam: dict, key: str):
    for fact in fam.get("facts") or []:
        if fact.get("key") == key and fact.get("status") == "active":
            return fact
    return None


def _check_arithmetic(families, parts, report: Report) -> None:
    for path, fam in families.values():
        for fact in fam.get("facts") or []:
            if fact.get("key") == "footprint.vendor_land_pattern":
                v = fact.get("value") or {}
                try:
                    if not math.isclose(2 * v["pad_length_D"] + v["gap_A"], v["span_B"], abs_tol=1e-6):
                        report.err(f"{path} [{fact['id']}]", "pad + gap + pad != span")
                except (KeyError, TypeError):
                    report.err(f"{path} [{fact.get('id')}]", "land pattern needs gap_A, span_B, pad_length_D")

    for path, part in parts.values():
        fam_entry = families.get(part.get("family"))
        if not fam_entry:
            continue
        fam = fam_entry[1]
        r_ohm = (part.get("decoded") or {}).get("resistance_ohm")
        for fact in part.get("facts") or []:
            if fact.get("key") != "voltage.rated" or fact.get("method") != "derived":
                continue
            power = _family_fact(fam, "power.rated")
            limit = _family_fact(fam, "voltage.limiting_element")
            if r_ohm is None or power is None or limit is None:
                report.err(f"{path} [{fact['id']}]", "cannot recompute: need resistance, rated power, limiting voltage")
                continue
            expected = min(math.sqrt(power["value"] * r_ohm), limit["value"])
            if abs(expected - fact["value"]) > 0.05:
                report.err(f"{path} [{fact['id']}]", f"stated {fact['value']} V, recomputed {expected:.1f} V")


def _check_cold(docs: dict, cold_root: Path, report: Report) -> None:
    for stem, d in docs.items():
        pdf = cold_root / d["cold_storage"]
        if not pdf.is_file():
            report.err(f"documents/{stem}.yaml", f"not in cold storage: {d['cold_storage']}")
            continue
        h = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if h != d["sha256"]:
            report.err(f"documents/{stem}.yaml", "cold storage file does not match sha256")
    report.notes.append(f"cold storage checked: {len(docs)} documents")


def cold_root_from_env() -> Path | None:
    base = os.environ.get("PCB_COLD_STORAGE")
    return Path(base) / "dkn-pcb-parts-db" if base else None
