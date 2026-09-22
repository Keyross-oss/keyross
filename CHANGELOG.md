# Changelog

## Unreleased
- cli: a missing file, an unsupported format or a missing directory is a usage error — clear message on stderr, exit 2, no report — instead of a red verdict or a traceback
- docs: `SECURITY.md` (private reporting, scope: false greens, network or file access during a check, unpinned changes, leaks into minimal feedback); README EN/FR — `einvoice` in the five-minute tour and in 0.1, `keyross add einvoice`; registry index and CI action point to the `Keyross-oss` organization
- **einvoice gauge 0.1.0** — the official CEN/TC 434 EN 16931 validation artefacts 1.3.16 (UBL, CII), vendored unmodified with their SHA-256 and executed offline by Saxon-HE (`pip install 'keyross[einvoice]'`); no rule rewritten
- adapters: one registry entry per rule id, read from the executed artifacts (1,562 ids, version = the release, fatal → red, warning → yellow); category = the rule id, XPath and assertion text in evidence only; refused as a hard red when the pin does not match, when the adapter needs the network, or when the document declares a DOCTYPE
- lock: records adapter pins (tool, version, per-artifact SHA-256) and every adapter rule; `lock --check` reports a changed release or artifact
- core: second canonical model `Invoice` (header, lines, totals, VAT breakdown; `InvoiceLine` extends the common `Line`) with UBL and CII loaders — standard library only
- cli: `check` and `gate` route `.xml` documents to the adapters of the loaded gauges; an XML document no gauge validates is a hard red
- badset: adapter bad cases (`badset/<gauge>.<rule>[.<variant>].xml`), one or more per rule family — 20 corrupted public Factur-X examples cover the 19 EN 16931 families; `keyross test` fails on an uncovered family
- fix(cli): force UTF-8 output — flags (✔ / ✘) crashed the CLI on a Windows console or pipe (cp1252)
- docs: last traces of the old vocabulary and of French removed from public files — `new_pack.md` issue template renamed `new_gauge.md`; comments in CI workflows, `pyproject.toml`, `keyross.yaml`, tests, `action/` and `demo-k8s/` translated; README points to each gauge's `adapters/`

## 0.1.0.dev0 — skeleton (21 September 2026)
- core: canonical document (xlsx, csv), Verdict, registry (@oracle, @contract, sentinels), runner, lock
- core gauge: schema, totals.match, duplicates, units.vocabulary, numbering.continuous, rows.conserved (sentinel); delete_rows contract
- gate: terminal and Markdown report, exit codes 0 / 1 / 2
- oracles: lint (no model, network, non-determinism), badset (tests for the tests)
- doctor: static checks (secrets, .env, Dockerfile, manifests, NetworkPolicy)
- adapters: Deep Agents middleware sketch; JSONL store
- 8 tests, complete badset for the core gauge, CLI — code, CLI and docs in English; French translations in *.fr.md
- docs: mission reframed — compilers for official documents, EU standards first; GAUGES.md reordered (core → einvoice → dora.register → aiact.annex4 → governance → security; construction as calibration field); Claude Code hook / plugin and MCP server named as distribution; full Apache-2.0 LICENSE, NOTICE, GOVERNANCE, CODE_OF_CONDUCT, issue and PR templates, DCO
- docs: landscape check — official validators exist (EN 16931 Schematron, DORA RoI validators, Annex IV scaffolds, agent governance planes); official-document gauges redefined as **adapters + delta oracles**, never reimplementations; mission reworded: make agents accountable to existing compilers, write the missing ones
- adapters: `ExternalValidatorAdapter` contract (pinned, offline, findings → verdicts, severity map, registry entries per rule id) + adapters/README; `adapters:` section in keyross.yaml; README: "pre-commit for agent outputs"
- product: the package manager — `docs/spec/gauge.md` (gauge.yaml with adapters pins, declared oracles, regulatory effective dates, signature), `gauges/index.json` (registry v1), `gauges/core/gauge.yaml`, commands `gauges` / `add` / `outdated`; README tagline "a compiler and a package manager for your agent's document oracles"; Semgrep-registry analogy
- docs: "a gauge is not a skill, a prompt or an instruction file" — comparison table in README EN/FR; rule in GAUGES, gauge spec (may / may not contain), CONTRIBUTING, GOVERNANCE, MANIFESTO; Claude Code integration described as a hook that executes code
- docs: architecture diagram (docs/architecture.svg/.png) — registry → installed gauges → three doors (harness middleware + Claude Code hook, MCP guard / tool mode, gate) → the same outputs; embedded in README EN/FR
- docs: animated loop (docs/loop.gif) — agent writes, compiler runs gauges, red verdict → revert + minimal feedback, retry → green, gate ships; simple overview diagram in README, detailed one in docs/ARCHITECTURE.md
- docs: animated "a skill asks, a gauge verifies" (docs/skills_vs_packs.gif) — the model's context vs the harness, the boundary, what crosses it; generation scripts kept outside the repo
- vocabulary: pack → **gauge**, adapters/ → **yoke/** (adapter contract moved to oracles/adapter.py), store → **telemetry**, verdict **flags** (green / yellow / red; black at scrutineering), **scrutineering** (the gate), **seal** (lock + attestation), `keyross yoke <harness>`; all docs, diagrams and animations regenerated; no French term in public documents
