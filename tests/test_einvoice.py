import copy
import socket
from pathlib import Path

import pytest
import yaml

from keyross import registry
from keyross.core.invoice import load_invoice
from keyross.core.runner import run_adapters
from keyross.core.verdict import Severity
import keyross.gauges.einvoice  # noqa: F401 — registers the adapter and its rules
from keyross.gauges.einvoice.adapters.schematron import GAUGE_DIR, CenSchematron, adapter

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "einvoice"
BADSET = sorted((ROOT / "badset").glob("einvoice.*.xml"))
CLEAN = sorted(FIXTURES.glob("*.xml"))

saxon = pytest.mark.skipif(__import__("importlib").util.find_spec("saxonche") is None, reason="pip install 'keyross[einvoice]'")


def test_one_registry_entry_per_rule_id_read_from_the_artifacts():
    rules = registry.all(kind="adapter", gauge="einvoice")
    assert len(rules) == len({r.id for r in adapter.rules()}) > 1500
    co10 = registry.get("einvoice.br-co-10")
    assert co10.version == "1.3.16" and co10.severity == Severity.HARD and "BT-106" in co10.doc
    assert registry.get("einvoice.ubl-cr-005").severity == Severity.SOFT          # warning → yellow
    assert registry.get("einvoice.br-51").severity == Severity.HARD               # fatal in CII, warning in UBL: the strictest is pinned


@saxon
@pytest.mark.parametrize("path", CLEAN, ids=lambda p: p.name)
def test_official_examples_are_green(path):
    rep = run_adapters(str(path))
    assert rep.exit_code == 0 and [v.oracle_id for v in rep.verdicts] == ["einvoice.schematron"]


@saxon
@pytest.mark.parametrize("path", BADSET, ids=lambda p: p.name)
def test_every_bad_case_raises_its_rule(path):
    rule = path.name.split(".")[1].upper()
    rep = run_adapters(str(path))
    v = next(v for v in rep.verdicts if v.failed and v.category == rule)
    assert v.oracle_id == f"einvoice.{rule.lower()}" and v.version == "1.3.16"
    assert v.evidence["occurrences"][0]["location"].startswith("/") and v.evidence["text"]
    assert v.minimal() == {"status": "fail", "flag": v.flag, "category": rule}     # no XPath, no assertion text
    assert rep.exit_code == (2 if rep.hard_failures else 1)


@saxon
def test_badset_covers_every_rule_family():
    results = adapter.badset(ROOT / "badset")
    assert results and all(ok for _, ok, _ in results), [r for r in results if not r[1]]


@saxon
def test_check_needs_no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network access during a check")
    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    fresh = CenSchematron.from_manifest()
    assert not [v for v in fresh.verdicts(FIXTURES / "facturx-en16931.ubl.xml") if v.failed]


def test_doctype_is_refused_before_parsing(tmp_path):
    f = tmp_path / "xxe.xml"
    f.write_text('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "http://127.0.0.1:9/">]>'
                 '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">&e;</Invoice>', encoding="utf-8")
    v, = adapter.verdicts(f)
    assert v.failed and v.category == "adapter.doctype_refused" and v.severity == Severity.HARD


def _manifest():
    return yaml.safe_load((GAUGE_DIR / "gauge.yaml").read_text(encoding="utf-8"))


def test_tampered_artifact_is_refused():
    m = _manifest()
    name = m["adapters"][0]["syntaxes"]["cii"]
    m["adapters"][0]["artifacts"][name] = "0" * 64
    v, = CenSchematron(m).verdicts(FIXTURES / "facturx-en16931.cii.xml")
    assert v.failed and v.category == "adapter.pin_mismatch" and v.severity == Severity.HARD


def test_adapter_that_needs_the_network_is_refused():
    m = copy.deepcopy(_manifest())
    m["adapters"][0]["offline"] = False
    v, = CenSchematron(m).verdicts(FIXTURES / "facturx-en16931.cii.xml")
    assert v.failed and v.category == "adapter.not_offline"


def test_lock_pins_the_adapter_and_its_rules(tmp_path):
    import json
    from keyross.core import lock
    p = tmp_path / "keyross.lock"
    data = lock.write(p)
    pin = data["adapters"]["einvoice.schematron"]
    assert pin["version"] == "1.3.16" and pin["offline"] is True and len(pin["artifacts"]) == 2
    assert data["oracles"]["einvoice.br-co-10"]["kind"] == "adapter" and lock.check(p) == []
    data["adapters"]["einvoice.schematron"]["artifact_sha256"] = "0" * 64
    p.write_text(json.dumps(data), encoding="utf-8")
    assert any("einvoice.schematron" in d for d in lock.check(p))


@pytest.mark.parametrize("name", ["facturx-en16931.cii.xml", "facturx-en16931.ubl.xml", "cen-cii-example1.xml", "cen-ubl-example1.xml"])
def test_invoice_loader_is_consistent_with_its_totals(name):
    inv = load_invoice(FIXTURES / name)
    assert inv.number and inv.currency and inv.issue_date and len(inv.issue_date) == 10 and inv.lines and inv.vat
    assert round(sum(l.amount for l in inv.lines), 2) == inv.totals.line_net                     # BR-CO-10
    assert round(sum(b.tax_amount for b in inv.vat), 2) == inv.totals.tax                          # BR-CO-14
    assert all(l.rid == f"rid:{l.number}" and l.vat_category for l in inv.lines)


def test_invoice_loaders_read_the_same_fields_in_both_syntaxes():
    cii, ubl = load_invoice(FIXTURES / "facturx-en16931.cii.xml"), load_invoice(FIXTURES / "facturx-en16931.ubl.xml")
    assert (cii.syntax, ubl.syntax) == ("cii", "ubl")
    for inv in (cii, ubl):
        assert inv.seller.name and inv.seller.country and inv.buyer.name and inv.totals.payable is not None


def test_credit_note_is_loaded():
    inv = load_invoice(FIXTURES / "cen-ubl-creditnote1.xml")
    assert inv.syntax == "ubl" and inv.type_code == "381" and inv.lines


def test_xml_without_a_gauge_is_refused(tmp_path):
    from keyross.oracles import adapter as adapter_mod
    f = tmp_path / "invoice.xml"; f.write_text("<x/>", encoding="utf-8")
    saved = dict(adapter_mod.adapters); adapter_mod.adapters.clear()
    try:
        rep = run_adapters(str(f))
    finally:
        adapter_mod.adapters.update(saved)
    assert rep.exit_code == 2 and rep.verdicts[0].category == "document.unsupported"
