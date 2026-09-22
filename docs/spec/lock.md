# Specification — keyross.lock (v0.1)

`keyross lock` writes, for every loaded oracle: `version`, `fingerprint` (short SHA-1 of the source code), `severity`, `kind`; and, for every installed gauge, its version and the checksums of the official artifacts its adapters execute.
`keyross lock --check` returns the differences: oracle changed, missing from the lock, or in the lock but not loaded. Empty = pinning respected.

A run must record the lock that verified it: it is the answer to "what verified this run?". The **seal** (0.3) freezes it with the verdicts and the document's hash, signed — the attestation an auditor verifies offline.
