"""The answer cache: an answer must cite records, and goes stale when those records change."""

import shutil
from pathlib import Path

import pytest
import yaml

from dkn_pcb_parts_db.cli import main
from dkn_pcb_parts_db.validate import validate

DATA = Path(__file__).resolve().parents[1] / "data"
FAMILY = Path("families/rohm/esr03-ezp.yaml")
ANSWERS = Path("answers/rohm/ESR03EZPF1002.yaml")
FAM_DOCS = ["5a31c213e43b1687", "13dac542f3d11c33", "69f60b9cd1643282", "ad8835947b625f9d"]

POWER = {
    "id": "ans.rohm.ESR03EZPF1002.power.rated",
    "question": "Rated power of ESR03EZPF1002?",
    "key": "power.rated",
    "answer": "0.33 W at 70 degC ambient (Rohm datasheet p.2); Digi-Key's 1/4 W loses.",
    "facts": ["rohm.esr03.power.rated"],
    "conflicts": ["rohm.ESR03EZPF1002.conflict.power"],
    "documents_seen": FAM_DOCS,
    "asked": [{"by": "test-board", "date": "2026-11-17"}],
    "answered": "2026-11-17",
    "status": "active",
}
PULSE = {
    "id": "ans.rohm.ESR03EZPF1002.pulse.rating",
    "question": "Pulse rating of ESR03EZPF1002?",
    "key": "pulse.rating",
    "answer": "Not known. No Rohm document seen states one; nearest are the overload and ESD tests.",
    "gaps": ["rohm.esr03.gap.pulse"],
    "documents_seen": FAM_DOCS,
    "asked": [{"by": "test-board", "date": "2026-11-17"}],
    "answered": "2026-11-17",
    "status": "active",
}


def write_answers(root: Path, *answers):
    path = root / ANSWERS
    path.parent.mkdir(parents=True, exist_ok=True)
    d = {"schema_version": 0, "subject": "rohm:ESR03EZPF1002", "answers": [dict(a) for a in answers]}
    path.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")


def edit(root: Path, rel: Path, change):
    path = root / rel
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(d)
    path.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")


@pytest.fixture
def data(tmp_path):
    dst = tmp_path / "data"
    shutil.copytree(DATA, dst)
    write_answers(dst, POWER, PULSE)
    return dst


def lookup(data, key):
    return main(["lookup", "rohm:ESR03EZPF1002", key, "--data", str(data)])


def test_good_answers_are_current(data):
    report = validate(data)
    assert report.ok, report.errors
    assert report.counts["answers"] == 2
    assert not report.stale
    assert lookup(data, "power.rated") == 0
    assert lookup(data, "pulse.rating") == 0
    assert lookup(data, "tcr") == 1


def test_superseded_fact_makes_answer_stale(data):
    def change(d):
        old = next(f for f in d["facts"] if f["id"] == "rohm.esr03.power.rated")
        old["status"] = "superseded"
        d["facts"].append({**old, "id": "rohm.esr03.power.rated.v2", "status": "active",
                           "supersedes": "rohm.esr03.power.rated"})
    edit(data, FAMILY, change)
    report = validate(data)
    assert report.ok, report.errors
    reasons = report.stale[POWER["id"]]
    assert "fact rohm.esr03.power.rated is superseded" in reasons
    assert any("rohm.esr03.power.rated.v2" in r for r in reasons)
    assert lookup(data, "power.rated") == 2


def test_gap_filled_makes_answer_stale(data):
    edit(data, FAMILY, lambda d: d["gaps"][0].update(status="resolved"))
    assert "gap rohm.esr03.gap.pulse is resolved" in validate(data).stale[PULSE["id"]]


def test_new_family_document_makes_gap_answer_stale(data):
    src = data / "documents" / "5a31c213e43b1687.yaml"
    d = yaml.safe_load(src.read_text(encoding="utf-8"))
    sha = "f" * 64
    d.update(sha256=sha, cold_storage=f"datasheets/{sha}.pdf")
    (data / "documents" / f"{sha[:16]}.yaml").write_text(yaml.safe_dump(d), encoding="utf-8")
    edit(data, FAMILY, lambda fam: fam["documents"].append(sha[:16]))
    report = validate(data)
    assert report.ok, report.errors
    assert any("gained document" in r for r in report.stale[PULSE["id"]])
    assert POWER["id"] not in report.stale  # fact answers go stale through superseding instead


def test_answer_must_cite_records(data):
    bare = {k: v for k, v in POWER.items() if k not in ("facts", "conflicts")}
    write_answers(data, bare)
    assert "answer must list the facts or gaps it used" in "\n".join(validate(data).errors)


def test_answer_unknown_fact(data):
    write_answers(data, {**POWER, "facts": ["rohm.nope"]})
    assert "uses unknown fact rohm.nope" in "\n".join(validate(data).errors)


def test_same_question_twice_must_supersede(data):
    write_answers(data, POWER, {**POWER, "id": "ans.dup"})
    assert "same question as active answer" in "\n".join(validate(data).errors)
    write_answers(data, {**POWER, "status": "superseded"},
                  {**POWER, "id": "ans.dup", "supersedes": POWER["id"]})
    assert validate(data).ok


def test_unknown_subject(data):
    edit(data, ANSWERS, lambda d: d.update(subject="rohm:NOPE"))
    assert "unknown subject rohm:NOPE" in "\n".join(validate(data).errors)


def test_lookup_refuses_invalid_data(data):
    write_answers(data, {**POWER, "facts": ["rohm.nope"]})
    assert lookup(data, "power.rated") == 3
