import keyross
from keyross import load, run, registry
from keyross.core.verdict import Status
import keyross.gauges.core  # noqa: F401 — registers the oracles


def test_load_and_blocks(good_doc):
    doc = load(good_doc)
    assert len(doc.lines) == 5 and len(doc.blocks()) == 2 and len(doc.amount_lines()) == 3
    assert doc.lines[0].rid == "rid:2"


def test_good_document_passes(good_doc):
    rep = run(load(good_doc), gauge="core", ctx={"units": ["m3", "m2"]})
    assert rep.exit_code == 0
    assert all(v.status != Status.FAIL for v in rep.verdicts)


def test_totals_mismatch_is_hard_failure(bad_totals_doc):
    rep = run(load(bad_totals_doc), gauge="core", ids=["core.totals.match"])
    v = rep.verdicts[0]
    assert v.failed and v.severity.value == "hard" and v.category == "totals.mismatch"
    assert v.evidence["errors"][0]["expected"] == 300.0
    assert rep.exit_code == 2
    assert v.minimal() == {"status": "fail", "flag": "red", "category": "totals.mismatch"}   # minimal feedback: flag + category, no evidence


def test_sentinel_conservation_is_silent(good_doc, bad_totals_doc):
    before, after = load(good_doc), load(bad_totals_doc)
    rep = run(after, gauge="core", ids=["core.rows.conserved"], ctx={"before": before})
    v = rep.verdicts[0]
    assert v.failed and v.silent
    assert rep.minimal() == []            # never returned to the agent
    assert rep.sentinel_failures and rep.exit_code == 0   # logged, not blocking on its own


def test_units_vocabulary_soft(good_doc):
    rep = run(load(good_doc), gauge="core", ids=["core.units.vocabulary"], ctx={"units": ["m3"]})
    v = rep.verdicts[0]
    assert v.failed and v.severity.value == "soft" and rep.exit_code == 1


def test_registry_and_lock(tmp_path, good_doc):
    from keyross.core import lock
    p = tmp_path / "keyross.lock"
    data = lock.write(p)
    assert "core.totals.match" in data["oracles"]
    assert lock.check(p) == []


def test_lint_refuses_llm_in_oracle(tmp_path):
    from keyross.oracles.lint import lint_file
    f = tmp_path / "bad_oracle.py"; f.write_text("import openai\nfrom keyross import oracle\n", encoding="utf-8")
    assert lint_file(f) and "openai" in lint_file(f)[0]


def test_contract_delete_rows(good_doc, tmp_path):
    from keyross.core.runner import run_contract
    from tests.conftest import make_xlsx
    before = load(good_doc)
    after_path = make_xlsx(tmp_path / "after.xlsx", [
        ("1.1", "Terrassement", "m3", 10, 25.0, 250.0),
        (None, "Sous-total lot 1", None, None, None, 300.0),
    ])
    after = load(after_path)
    verdicts = run_contract("delete_rows", before, after, {"target_rows": ["rid:3"]})
    assert verdicts and verdicts[0].failed and verdicts[0].category == "contract.delete.amount_row"


def test_cli_refuses_a_missing_file_without_a_report(tmp_path, capsys, monkeypatch):
    from keyross.cli import main
    monkeypatch.chdir(tmp_path)
    assert main(["check", str(tmp_path / "missing.xml")]) == 2
    assert "no such file" in capsys.readouterr().err
    assert not (tmp_path / ".keyross").exists()                       # no report for a document that does not exist
    (tmp_path / "keyross.yaml").write_text("gauges: [core]\n", encoding="utf-8")
    (tmp_path / "notes.yaml").write_text("a: 1\n", encoding="utf-8")
    assert main(["check", "notes.yaml"]) == 2 and "unsupported format" in capsys.readouterr().err
    assert main(["gate", "no-such-dir"]) == 2


def test_yoke_exports_and_first_pass_rate(good_doc, bad_totals_doc):
    from keyross.yoke import Yoke, KeyrossMiddleware
    assert KeyrossMiddleware is Yoke and Yoke(gauge="core").gauge == "core"
    assert run(load(good_doc), gauge="core", ctx={"units": ["m3", "m2"]}).aligned          # first pass: green, no retry
    assert not run(load(bad_totals_doc), gauge="core", ids=["core.totals.match"]).aligned
