# Keyross gate — GitHub Action

Replays the gate on a folder of agent outputs in CI: every loaded gauge, outside the agent, with the exit code as the verdict. It is the same `keyross gate` you run locally.

```yaml
- uses: actions/checkout@v4
- uses: Keyross-oss/keyross/integrations/github-action@v0.1.2
  with:
    path: outputs/                 # the folder the agent wrote
    spec: "keyross[einvoice]"      # what pip installs: a version, extras, or a path
```

| Input | Default | |
|---|---|---|
| `path` | — | the folder to gate (xlsx, csv, xml), relative to `working-directory` |
| `spec` | `keyross` | what pip installs, e.g. `keyross[einvoice]==0.1.2` |
| `fail-on` | `hard` | `hard` fails the step on a red flag; `soft` on a yellow flag too |
| `working-directory` | `.` | where `keyross.yaml` lives — it says which gauges to load |
| `python-version` | `3.12` | |

The step fails when the gate exits 2 (a red flag), or 1 (a yellow flag) with `fail-on: soft`. The verdicts are printed in the job log; nothing leaves the runner. This repository runs the action on itself on every commit: green on clean invoices, red on its bad set (`.github/workflows/ci.yml`, job `action`).
