"""The validator must pass the real data and catch each kind of damage."""

import shutil
from pathlib import Path

import pytest
import yaml

from dkn_pcb_parts_db.cli import main
from dkn_pcb_parts_db.validate import validate

DATA = Path(__file__).resolve().parents[1] / "data"
FAMILY = Path("families/rohm/esr03-ezp.yaml")
PART = Path("parts/rohm/ESR03EZPF1002.yaml")


@pytest.fixture
def data(tmp_path):
    dst = tmp_path / "data"
    shutil.copytree(DATA, dst)
    return dst


def edit(root: Path, rel: Path, change):
    path = root / rel
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(d)
    path.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")


def fact(d, fid):
    return next(f for f in d["facts"] if f["id"] == fid)


def errors(root):
    report = validate(root)
    return "\n".join(report.errors)


def test_real_data_passes():
    report = validate(DATA)
    assert report.ok, report.errors
    assert report.counts["facts"] > 0


def test_cli_exit_codes(data, capsys):
    assert main(["validate", "--data", str(data)]) == 0
    edit(data, FAMILY, lambda d: fact(d, "rohm.esr03.size").update(trust="sure"))
    assert main(["validate", "--data", str(data)]) == 1


def test_duplicate_fact_id(data):
    edit(data, FAMILY, lambda d: d["facts"].append(dict(d["facts"][0])))
    assert "duplicate id rohm.esr03.size" in errors(data)


def test_unknown_document_citation(data):
    edit(data, FAMILY, lambda d: fact(d, "rohm.esr03.size")["source"].update(doc="0000000000000000"))
    assert "cites unknown document 0000000000000000" in errors(data)


def test_unknown_trust_level(data):
    edit(data, FAMILY, lambda d: fact(d, "rohm.esr03.size").update(trust="pretty-sure"))
    assert "unknown trust" in errors(data)


def test_per_row_trust_needs_each_row(data):
    edit(data, FAMILY, lambda d: fact(d, "rohm.esr03.tcr")["value"][0].pop("trust"))
    assert "row 0: missing or unknown trust" in errors(data)


def test_land_pattern_arithmetic(data):
    edit(data, FAMILY, lambda d: fact(d, "rohm.esr03.land_pattern")["value"].update(span_B=2.2))
    assert "pad + gap + pad != span" in errors(data)


def test_rated_voltage_recomputed(data):
    edit(data, PART, lambda d: fact(d, "rohm.ESR03EZPF1002.voltage.rated").update(value=60.0))
    assert "recomputed 57.4 V" in errors(data)


def test_derived_fact_input_must_exist(data):
    edit(data, PART, lambda d: fact(d, "rohm.ESR03EZPF1002.voltage.rated")["inputs"].append("rohm.nope"))
    assert "unknown input rohm.nope" in errors(data)


def test_fact_needs_a_source(data):
    edit(data, FAMILY, lambda d: fact(d, "rohm.esr03.size").pop("source"))
    assert "needs a source" in errors(data)


def test_document_name_must_match_hash(data):
    src = data / "documents" / "5a31c213e43b1687.yaml"
    src.rename(data / "documents" / "1111111111111111.yaml")
    out = errors(data)
    assert "file name must be the first 16 hex of sha256" in out
    assert "cites unknown document 5a31c213e43b1687" in out


def test_part_must_point_to_known_family(data):
    edit(data, PART, lambda d: d.update(family="rohm.nope"))
    assert "unknown family rohm.nope" in errors(data)


def test_gap_status(data):
    edit(data, FAMILY, lambda d: d["gaps"][0].update(status="maybe"))
    assert "status must be one of" in errors(data)


def test_cold_storage_mismatch(data, tmp_path):
    cold = tmp_path / "cold"
    (cold / "datasheets").mkdir(parents=True)
    report = validate(data, cold)
    assert any("not in cold storage" in e for e in report.errors)
    d = yaml.safe_load((data / "documents" / "5a31c213e43b1687.yaml").read_text(encoding="utf-8"))
    (cold / d["cold_storage"]).write_bytes(b"not the pdf")
    report = validate(data, cold)
    assert any("does not match sha256" in e for e in report.errors)
