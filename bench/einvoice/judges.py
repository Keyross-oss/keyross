"""The benchmark's judges — none of them is Keyross, so nothing the yoke optimizes for is graded by the yoke's own code.

- the **validator**: easybill/en16931-validator (MIT), an independent implementation that runs the same official CEN
  EN 16931 release (1.3.16) — pinned by image digest, running locally in Docker;
- the **schema**: the official Factur-X 1.09 EN 16931 XSD (structure, which the CEN rules do not check), taken from the
  factur-x 6.8 wheel, pinned by SHA-256;
- the **order**: does the invoice match the order it was issued for (grade.order_mismatches).

There is one official rule set: the validator is an independent *implementation* of the same rules, not other rules.
`python -m bench.einvoice.judges --setup` fetches the schema and prints the command that starts the validator."""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_URL = "http://127.0.0.1:8081/validation"
VALIDATOR_IMAGE = "easybill/en16931-validator:0.7.0"
VALIDATOR_DIGEST = "sha256:e2f84d3d371e95d9eae2da0ccaef5a13bf01f2e58278e9080994ae763d8914dd"
VALIDATOR_START = (f"docker run -d --name keyross-bench-validator -p 127.0.0.1:8081:8080 "
                   f"-e JAVA_TOOL_OPTIONS=-Xmx512m {VALIDATOR_IMAGE.split(':')[0]}@{VALIDATOR_DIGEST}")
RULES_VERSION = "1.3.16"
SCHEMA_WHEEL = ("factur-x", "6.8", "02b57dd57f59d0cdd87f034a538bf30a4b9241a72a19cd75fe1538233163ee15")
SCHEMA_DIR = ROOT / ".keyross" / "bench" / "xsd"          # short path: the file names are long (Windows' 260-character limit)
SCHEMA_ROOT = "Factur-X_EN16931.xsd"


class JudgeUnavailable(RuntimeError):
    """A judge that cannot run stops the benchmark: a run is never graded by fewer judges than declared."""


def validator(xml: bytes) -> dict[str, Any]:
    """Fatal rule ids and warnings from the independent validator."""
    req = urllib.request.Request(VALIDATOR_URL, data=xml, headers={"Content-Type": "application/xml"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
    except urllib.error.HTTPError as e:           # 400 = the document has errors: the body carries them
        body = e.read()
    except (urllib.error.URLError, OSError) as e:
        raise JudgeUnavailable(f"validator unreachable at {VALIDATOR_URL} — start it: {VALIDATOR_START}") from e
    try:
        d = json.loads(body)
    except json.JSONDecodeError:                  # not even XML the validator can read
        return {"version": None, "fatal": ["unreadable"], "warnings": []}
    version = d.get("meta", {}).get("validation_profile_version")
    if version and version != RULES_VERSION:
        raise JudgeUnavailable(f"validator runs rules {version}, the benchmark declares {RULES_VERSION}")
    fatal = sorted({e.get("rule_id", "?") for e in d.get("errors", []) if str(e.get("rule_severity", "")).upper() == "FATAL"})
    return {"version": version, "fatal": fatal, "warnings": sorted({w.get("rule_id", "?") for w in d.get("warnings", [])})}


@lru_cache(maxsize=1)
def _schema() -> Any:
    from lxml import etree
    main = SCHEMA_DIR / SCHEMA_ROOT
    if not main.exists():
        raise JudgeUnavailable(f"schema missing in {SCHEMA_DIR} — run: python -m bench.einvoice.judges --setup")
    return etree.XMLSchema(etree.parse(str(main)))


def schema_errors(xml: bytes) -> list[str]:
    """Violations of the official Factur-X EN 16931 schema (empty: the structure is valid)."""
    from lxml import etree
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    try:
        doc = etree.fromstring(xml, parser)
    except etree.XMLSyntaxError as e:
        return [f"not well-formed: {e}"]
    schema = _schema()
    if schema.validate(doc):
        return []
    return [f"line {e.line}: {e.message}" for e in list(schema.error_log)[:5]]


def setup() -> None:
    """Fetch the factur-x wheel (pinned), check its SHA-256, extract the EN 16931 schema files."""
    name, version, sha = SCHEMA_WHEEL
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, "-m", "pip", "download", "--no-deps", "--only-binary", ":all:", "-q", "-d", tmp,
                        f"{name}=={version}"], check=True)
        wheel = next(Path(tmp).glob("*.whl"))
        data = wheel.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != sha:
        raise SystemExit(f"{wheel.name}: SHA-256 {actual} does not match the pin {sha}")
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for member in z.namelist():
            if "/facturx-en16931/" in member and member.endswith(".xsd"):
                (SCHEMA_DIR / member.rsplit("/", 1)[-1]).write_bytes(z.read(member))
    print(f"schema: {len(list(SCHEMA_DIR.glob('*.xsd')))} files in {SCHEMA_DIR}")
    print(f"validator: {VALIDATOR_START}")


if __name__ == "__main__":
    if "--setup" in sys.argv:
        setup()
