# Security policy

Keyross decides whether an agent's output may ship. A way to get a wrong green — or to make a check reach the network — is a security issue, not just a bug.

## Reporting a vulnerability

Please **do not open a public issue**. Report it privately through GitHub: **Security → Report a vulnerability** on this repository. We acknowledge within 3 working days and keep you informed until the fix is released; you are credited unless you prefer otherwise.

## In scope

- a document that makes an oracle or an adapter return green where it should be red, or skip silently;
- anything that makes `keyross check`, `gate` or `test` reach the network, read files outside the document, or execute code from the document (external entities, DOCTYPE, XSLT or Schematron injection);
- a way to change a pinned artifact or oracle without `keyross lock --check` reporting it;
- evidence, secrets or rule logic leaking into the minimal feedback (`Verdict.minimal()`) returned to the agent.

## Out of scope

- errors in the official rules themselves (for example the CEN EN 16931 artefacts): report them upstream; we pin the fixed release once published;
- findings that require a modified gauge or a tampered local installation.

## Supported versions

Keyross is pre-1.0: only the latest release receives fixes.
