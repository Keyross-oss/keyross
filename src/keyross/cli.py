"""keyross — the command line. init · check · gate · test · lint · lock · doctor · gauges · add · outdated · yoke · stats. No account, no cloud, no model."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import yaml

from keyross import __version__
from keyross.core.runner import ADAPTER_SUFFIXES, TABULAR_SUFFIXES, check_file, unreadable
from keyross.core import lock as lockmod
from keyross.gate import report as reportmod
from keyross.oracles.badset import run_badset
from keyross.oracles.lint import lint_dir
from keyross.gauges import load_gauge

DEFAULT_CONFIG = """# keyross.yaml — the configuration of your agent's compiler
gauges: [core]            # gauges to load (modules keyross.gauges.<name>); add your own: [core, mycompany.invoices]
adapters: []             # official validators to run, pinned (empty = every adapter of the loaded gauges), e.g. [einvoice.schematron]
oracles_dir: oracles     # your own oracles (@oracle, @contract)
badset_dir: badset       # one bad case per oracle of yours: badset/<oracle_id>.xlsx|csv (a gauge ships its own)
context:
  units: [u, m, m2, m3, ml, kg, t, ens, ff, h, j, l]   # unit vocabulary — adapt it
report_dir: .keyross/reports
"""

SAMPLE_ORACLE = '''"""Your own oracles. An oracle = a pure function (document, context) -> Verdict. Deterministic or nothing."""
from keyross import oracle, Verdict


@oracle("mine.total.positive", severity="soft")
def total_positive(doc):
    """No negative amount in this kind of document."""
    bad = [{"rid": l.rid, "amount": l.amount} for l in doc.amount_lines() if (l.amount or 0) < 0]
    return Verdict.fail(f"{len(bad)} negative amount(s)", "amount.negative", rows=bad) if bad else Verdict.ok()
'''

# the bad case of the sample oracle: a table with a negative amount, which mine.total.positive must catch (keyross test)
SAMPLE_BAD_CASE = """designation;qty;unit;unit_price;amount
Office chair;3;u;49.90;149.70
Credit;1;u;-20.00;-20.00
"""


def _load_config(path: str = "keyross.yaml") -> dict:
    p = Path(path)
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else yaml.safe_load(DEFAULT_CONFIG)


def _load_oracles(cfg: dict) -> None:
    for gauge in cfg.get("gauges", []):
        load_gauge(gauge)
    d = Path(cfg.get("oracles_dir", "oracles"))
    if d.exists():
        for f in sorted(d.glob("*.py")):
            spec = importlib.util.spec_from_file_location(f"oracles_{f.stem}", f)
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)  # type: ignore[union-attr]


def cmd_init(args: argparse.Namespace) -> int:
    Path("keyross.yaml").write_text(DEFAULT_CONFIG, encoding="utf-8")
    Path("oracles").mkdir(exist_ok=True); Path("badset").mkdir(exist_ok=True)
    Path("oracles/mine.py").write_text(SAMPLE_ORACLE, encoding="utf-8")
    Path("badset/mine.total.positive.csv").write_text(SAMPLE_BAD_CASE, encoding="utf-8")
    print("created keyross.yaml, oracles/mine.py, badset/mine.total.positive.csv.\n"
          "Next: keyross check <file.xlsx> · for EN 16931 invoices, first: keyross add einvoice")
    return 0


def _fail(message: str) -> int:
    """A usage error (missing file, unsupported format): a clear message, no report, exit 2 — never a verdict on a document."""
    print(f"keyross: {message}", file=sys.stderr)
    return 2


def cmd_check(args: argparse.Namespace) -> int:
    if not Path(args.file).is_file():
        return _fail(f"no such file: {args.file}")
    cfg = _load_config(); _load_oracles(cfg)
    try:
        rep = check_file(args.file, gauge=args.gauge, ctx=dict(cfg.get("context", {})), only=cfg.get("adapters") or None,
                         before=args.before)
    except (ValueError, OSError) as e:
        return _fail(str(e))
    if args.json:
        print(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2, default=str))
    else:
        print(reportmod.terminal(rep, verbose=args.verbose))
        rd = Path(cfg.get("report_dir", ".keyross/reports")); rd.mkdir(parents=True, exist_ok=True)
        out = rd / (Path(args.file).stem + ".md"); out.write_text(reportmod.markdown(rep), encoding="utf-8")
        print(f"report: {out}")
    return rep.exit_code


def cmd_gate(args: argparse.Namespace) -> int:
    """The gate: every file of a folder; exit 2 on any hard red, 1 on soft (depending on --fail-on)."""
    if not Path(args.dir).is_dir():
        return _fail(f"no such directory: {args.dir}")
    cfg = _load_config(); _load_oracles(cfg)
    worst = 0
    for f in sorted(p for p in Path(args.dir).iterdir() if p.suffix.lower() in (*TABULAR_SUFFIXES, *ADAPTER_SUFFIXES)):
        try:
            rep = check_file(f, gauge=args.gauge, ctx=dict(cfg.get("context", {})), only=cfg.get("adapters") or None)
        except (ValueError, OSError) as e:        # an output nothing can read is a red, not a skip
            rep = unreadable(str(f), str(e))
        print(reportmod.terminal(rep)); worst = max(worst, rep.exit_code)
    if args.fail_on == "hard":
        return 2 if worst == 2 else 0
    return worst


def cmd_test(args: argparse.Namespace) -> int:
    cfg = _load_config(); _load_oracles(cfg)
    rc = 0
    for oid, ok, msg in run_badset(cfg.get("badset_dir", "badset"), gauge=args.gauge, ctx=dict(cfg.get("context", {})),
                                   gauges=cfg.get("gauges", [])):
        print(f"  {'✔' if ok else '✘'} {oid:<28} {msg}"); rc = rc or (0 if ok else 1)
    return rc


def cmd_lint(args: argparse.Namespace) -> int:
    cfg = _load_config()
    targets = [Path(cfg.get("oracles_dir", "oracles")), Path(__file__).parent / "gauges"]
    problems = [p for t in targets if t.exists() for p in lint_dir(t)]
    for p in problems:
        print("  ✘ " + p)
    print("  ✔ no model, no network, no non-determinism inside the oracles" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def cmd_lock(args: argparse.Namespace) -> int:
    cfg = _load_config(); _load_oracles(cfg)
    if args.check:
        diffs = lockmod.check()
        for d in diffs:
            print("  ✘ " + d)
        print("  ✔ pinning respected" if not diffs else f"{len(diffs)} difference(s) with keyross.lock")
        return 1 if diffs else 0
    data = lockmod.write()
    print(f"keyross.lock written — {len(data['oracles'])} oracle(s) pinned")
    return 0


def _index() -> dict:
    return json.loads((Path(__file__).parent / "gauges" / "index.json").read_text(encoding="utf-8"))["gauges"]


def _gauge_version(name: str) -> str | None:
    p = Path(__file__).parent / "gauges" / name / "gauge.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")).get("version") if p.exists() else None


def cmd_gauges(args: argparse.Namespace) -> int:
    """Installed gauges vs the registry index."""
    cfg = _load_config(); idx = _index()
    print(f"  {'gauge':<16} {'installed':<11} {'latest':<9} status")
    for name, meta in idx.items():
        installed = _gauge_version(name) if name in cfg.get("gauges", []) else None
        latest = meta.get("latest") or "—"
        status = "installed" if installed else ("available" if meta.get("latest") else meta.get("status", "planned"))
        print(f"  {name:<16} {installed or '—':<11} {latest:<9} {status}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    """Add a gauge from the registry index to keyross.yaml (v1: built-in gauges; git sources in 0.3)."""
    name = args.gauge.split("@")[0]; idx = _index()
    if name not in idx:
        print(f"unknown gauge: {name} — see `keyross gauges`"); return 1
    src = idx[name]["source"]
    if not src.startswith("builtin:"):
        print(f"{name}: source {src} — installing from git arrives in 0.3; the gauge is {idx[name].get('status', 'planned')}"); return 1
    cfg = _load_config()
    if name in cfg.get("gauges", []):
        print(f"{name} already in keyross.yaml"); return 0
    cfg.setdefault("gauges", []).append(name)
    Path("keyross.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"added {name}@{_gauge_version(name)} to keyross.yaml — run `keyross lock`")
    return 0


def cmd_outdated(args: argparse.Namespace) -> int:
    """Are we on the latest rules? Installed gauge versions vs the registry."""
    cfg = _load_config(); idx = _index(); rc = 0
    for name in cfg.get("gauges", []):
        installed, latest = _gauge_version(name), idx.get(name, {}).get("latest")
        if latest and installed and installed != latest:
            print(f"  ✘ {name:<16} {installed} → {latest}"); rc = 1
        else:
            print(f"  ✔ {name:<16} {installed or '?'} (latest)")
    return rc


def cmd_yoke(args: argparse.Namespace) -> int:
    """The yoke: couple an agent to its gauges (0.2: prints the integration recipe for the chosen harness)."""
    recipes = {
        "deepagents": ("# pip install 'keyross[yoke]'\nfrom keyross.yoke import Yoke\nfrom keyross.telemetry import JsonlTelemetry\n"
                       "agent = create_deep_agent(..., middleware=[Yoke(gauge=\"einvoice\", telemetry=JsonlTelemetry())])\n"
                       "# another backend than the default StateBackend? pass the same one: Yoke(..., backend=backend)\n"
                       "# then: keyross stats   (first-pass rate)"),
        "claude-code": "# .claude/settings.json → hooks.PostToolUse: on Write|Edit run `keyross check \"$FILE\" --json`\n# code executed by the harness — not a skill the model reads",
        "mcp": "keyross serve --mcp --mode guard   # 0.5 — called by the platform; --mode tool exposes verify with minimal feedback",
    }
    if args.harness not in recipes:
        print(f"unknown harness: {args.harness} — one of {', '.join(recipes)}"); return 1
    print(recipes[args.harness]); return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """The first-pass rate of the yokes, from the telemetry: green on the first write, no retry."""
    from keyross.telemetry import first_pass, read_events
    stats = first_pass(read_events(args.telemetry))
    if args.json:
        print(json.dumps(stats, indent=2)); return 0
    if not stats:
        print(f"no verification event in {args.telemetry} — give the yoke a telemetry: Yoke(..., telemetry=JsonlTelemetry())"); return 0
    print(f"  {'gauge':<12} {'documents':>9} {'first pass':>10} {'rate':>6} {'writes':>7} {'pit stops':>9}")
    for gauge, s in stats.items():
        rate = "—" if s["first_pass_rate"] is None else f"{s['first_pass_rate']:.0%}"
        print(f"  {gauge:<12} {s['documents']:>9} {s['first_pass']:>10} {rate:>6} {s['writes']:>7} {s['pit_stops']:>9}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    from keyross.doctor.checks import run_static, render
    findings = run_static(args.path)
    print(render(findings))
    return 0 if all(f.ok for f in findings) else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="keyross", description="A compiler for your agent's outputs.")
    p.add_argument("--version", action="version", version=f"keyross {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="create keyross.yaml, oracles/, badset/").set_defaults(fn=cmd_init)
    c = sub.add_parser("check", help="run the oracles on one output"); c.add_argument("file"); c.add_argument("--gauge"); c.add_argument("--before", help="reference document (conservation sentinel)")
    c.add_argument("--json", action="store_true"); c.add_argument("-v", "--verbose", action="store_true"); c.set_defaults(fn=cmd_check)
    g = sub.add_parser("gate", help="the gate on a folder of outputs — exit code for CI"); g.add_argument("dir"); g.add_argument("--gauge"); g.add_argument("--fail-on", choices=["hard", "soft"], default="hard"); g.set_defaults(fn=cmd_gate)
    t = sub.add_parser("test", help="does every oracle catch its bad case from the badset?"); t.add_argument("--gauge"); t.set_defaults(fn=cmd_test)
    sub.add_parser("lint", help="refuse an oracle that calls a model or the network").set_defaults(fn=cmd_lint)
    lk = sub.add_parser("lock", help="pin the oracles (keyross.lock)"); lk.add_argument("--check", action="store_true"); lk.set_defaults(fn=cmd_lock)
    d = sub.add_parser("doctor", help="is the agent ready for a cluster? (v0.1: static checks)"); d.add_argument("path", nargs="?", default="."); d.set_defaults(fn=cmd_doctor)
    sub.add_parser("gauges", help="installed gauges vs the registry index").set_defaults(fn=cmd_gauges)
    a = sub.add_parser("add", help="add a gauge from the registry (keyross add core)"); a.add_argument("gauge"); a.set_defaults(fn=cmd_add)
    sub.add_parser("outdated", help="are we on the latest rules? installed gauges vs registry").set_defaults(fn=cmd_outdated)
    y = sub.add_parser("yoke", help="couple an agent to its gauges: deepagents · claude-code · mcp"); y.add_argument("harness"); y.set_defaults(fn=cmd_yoke)
    st = sub.add_parser("stats", help="first-pass rate of the yokes, from the telemetry"); st.add_argument("--telemetry", default=".keyross/events.jsonl")
    st.add_argument("--json", action="store_true"); st.set_defaults(fn=cmd_stats)
    args = p.parse_args(argv)
    _utf8_output()
    return args.fn(args)


def _utf8_output() -> None:
    """Flags are printed with ✔ / ✘; a Windows console or pipe defaults to cp1252, which cannot encode them."""
    for stream in (sys.stdout, sys.stderr):
        if (getattr(stream, "encoding", "") or "").lower().replace("-", "") != "utf8" and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
