# Specification — the verdict (v0.1)

An oracle returns a **verdict**: `status` (ok | fail | skip), `message`, `category`, `evidence` (dict), `oracle_id`, `version`, `severity` (hard | soft), `silent` (bool), and a derived **`flag`**: green (ok / skip), yellow (soft failure), red (hard failure).

- `minimal()` — what the agent receives: `{"status", "flag", "category"}`. Never `evidence`, never the list of oracles, never the sentinels. Red means pit stop: revert and retry.
- `to_dict()` — what the telemetry and the report receive: everything.
- `impact` (optional, 0.2): an estimated magnitude of the deviation in the document's own unit (an amount, a count), used to prioritize fixes and to weight yellow flags. Each gauge states how it estimates it and from which source.
- A `skip` is not a failure: the oracle does not apply (no vocabulary, no reference document).
- An oracle that raises produces a `fail` of category `oracle.error`, with the oracle's severity. We never guess.

The report of a run: `Report` — `verdicts`, `flag` (green | yellow | red), `exit_code` (0 / 1 / 2), `hard_failures`, `soft_failures`, `sentinel_failures`, `minimal()`.

**Black flag.** Scrutineering raises it when the agent's flag was green and the gate's is red: an integrity incident — the run is quarantined, never a grade.
