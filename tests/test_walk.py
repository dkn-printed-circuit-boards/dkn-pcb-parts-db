"""Random walks: tasks must be blind, scoring must catch a wrong value."""

import shutil
from pathlib import Path

import pytest
import yaml

from dkn_pcb_parts_db import walk
from dkn_pcb_parts_db.validate import validate

DATA = Path(__file__).resolve().parents[1] / "data"
FAMILY = Path("families/rohm/esr03-ezp.yaml")


@pytest.fixture
def data(tmp_path):
    dst = tmp_path / "data"
    shutil.copytree(DATA, dst)
    return dst


def family():
    return yaml.safe_load((DATA / FAMILY).read_text(encoding="utf-8"))


def leaves(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if k != "applies_to":
                yield from leaves(v)
    elif isinstance(x, list):
        for v in x:
            yield from leaves(v)
    else:
        yield x


def test_tasks_are_blind_and_reproducible(monkeypatch):
    monkeypatch.delenv("PCB_COLD_STORAGE", raising=False)
    tasks, key = walk.pick(DATA, 50, seed=1)
    assert tasks == walk.pick(DATA, 50, seed=1)[0]
    for t in tasks["tasks"]:
        assert all(v is None for v in leaves(t["template"])), t["task"]
        assert "trust" not in str(t["template"])
    picked = set(key["records"].values())
    assert "rohm.ESR03EZPF1002.voltage.rated" not in picked  # derived: validate recomputes it
    assert "rohm.esr03.gap.pulse" in picked


def results_from_records(key, override=None):
    fam = family()
    facts = {f["id"]: f for f in fam["facts"]}
    out = []
    for tid, rid in key["records"].items():
        value = facts[rid]["value"] if rid in facts else {"found": False, "value": None, "page": None}
        out.append({"task": tid, "value": (override or {}).get(rid, value)})
    return {"results": out}


def test_score_agrees_with_true_values():
    _, key = walk.pick(DATA, 50, seed=2)
    log = walk.score(DATA, key, results_from_records(key), "2026-11-17", "test")
    assert {r["verdict"] for r in log["results"]} == {"agree"}


def test_score_catches_wrong_value_and_row():
    _, key = walk.pick(DATA, 50, seed=3)
    tcr = [dict(r) for r in next(f for f in family()["facts"] if f["id"] == "rohm.esr03.tcr")["value"]]
    tcr[3]["ppm_per_c"] = 100  # J row is 200 in the datasheet
    log = walk.score(DATA, key, results_from_records(key, {"rohm.esr03.size": "0402", "rohm.esr03.tcr": tcr}),
                     "2026-11-17", "test")
    by = {r["record"]: r for r in log["results"]}
    assert by["rohm.esr03.size"]["verdict"] == "disagree"
    assert by["rohm.esr03.tcr"]["rows_agreed"] == [0, 1, 2]
    assert by["rohm.esr03.tcr"]["diffs"][0]["path"] == "value[3].ppm_per_c"


def test_gap_found_is_a_disagreement():
    _, key = walk.pick(DATA, 50, seed=4)
    found = {"rohm.esr03.gap.pulse": {"found": True, "value": "1 W for 1 ms", "page": 9}}
    log = walk.score(DATA, key, results_from_records(key, found), "2026-11-17", "test")
    assert next(r for r in log["results"] if r["record"] == "rohm.esr03.gap.pulse")["verdict"] == "disagree"


def test_walked_records_get_picked_less(data):
    def weight(rid):
        return next(w for r, w, _ in walk.candidates(data) if r == rid)
    before = weight("rohm.esr03.size")
    log = {"schema_version": 0, "date": "2026-11-18", "seed": 9, "walker": "test",
           "results": [{"record": "rohm.esr03.size", "verdict": "agree"}]}
    (data / "walks").mkdir(exist_ok=True)
    (data / "walks" / "2026-11-18-s9.yaml").write_text(yaml.safe_dump(log), encoding="utf-8")
    assert weight("rohm.esr03.size") == before / 2
    assert validate(data).ok


def test_walk_log_must_name_known_records(data):
    log = {"schema_version": 0, "date": "2026-11-18", "seed": 9, "walker": "test",
           "results": [{"record": "rohm.nope", "verdict": "maybe"}]}
    (data / "walks").mkdir(exist_ok=True)
    (data / "walks" / "2026-11-18-s9.yaml").write_text(yaml.safe_dump(log), encoding="utf-8")
    out = "\n".join(validate(data).errors)
    assert "walked unknown record rohm.nope" in out
    assert "verdict must be one of" in out
