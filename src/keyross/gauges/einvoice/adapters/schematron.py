"""einvoice.schematron — the official CEN/TC 434 EN 16931 validation artefacts, executed as published. No rule is rewritten.

The XSLT 2.0 files compiled by CEN from the Schematron are vendored under rules/, checked against the SHA-256 of gauge.yaml
before they run, and executed offline by Saxon-HE (saxonche). Every failed assertion of the SVRL output is a finding;
the rule list the registry pins is read from the same artifacts. A verdict that differs from the official validator is a bug here."""
from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

import yaml

from keyross.core.invoice import parse_xml, syntax_of
from keyross.oracles.adapter import AdapterError, AdapterPin, ExternalValidatorAdapter, Finding, Rule

GAUGE_DIR = Path(__file__).resolve().parent.parent
XSL = "{http://www.w3.org/1999/XSL/Transform}"
SVRL = "{http://purl.oclc.org/dsdl/svrl}"

_processor: Any = None


def _saxon() -> Any:
    """One Saxon-HE processor per process (creating several is slow and unsupported by saxonche)."""
    global _processor
    if _processor is None:
        try:
            from saxonche import PySaxonProcessor
        except ImportError as e:
            raise AdapterError("saxonche is not installed — pip install 'keyross[einvoice]'", "adapter.unavailable") from e
        _processor = PySaxonProcessor(license=False)
    return _processor


class CenSchematron(ExternalValidatorAdapter):
    id = "einvoice.schematron"
    gauge = "einvoice"

    def __init__(self, manifest: dict[str, Any], root: Path = GAUGE_DIR) -> None:
        m = next(a for a in manifest["adapters"] if a["id"] == self.id)
        self.root, self.syntaxes = root, dict(m["syntaxes"])
        self.engine = m.get("engine", "")
        artifacts = {str(k): str(v) for k, v in m["artifacts"].items()}
        self._pin = AdapterPin(tool=m["tool"], version=str(m["version"]), artifacts=artifacts,
                               artifact_sha256=AdapterPin.digest(artifacts), offline=bool(m.get("offline", True)))
        self._verified: dict[str, Path] = {}
        self._compiled: dict[str, Any] = {}

    @classmethod
    def from_manifest(cls, path: Path = GAUGE_DIR / "gauge.yaml") -> "CenSchematron":
        return cls(yaml.safe_load(path.read_text(encoding="utf-8")), path.parent)

    def pin(self) -> AdapterPin:
        return self._pin

    def _artifact(self, syntax: str) -> Path:
        """The artifact of a syntax, after its SHA-256 matched the pin — otherwise nothing runs."""
        if syntax not in self._verified:
            name = self.syntaxes[syntax]
            path = self.root / name
            if not path.exists():
                raise AdapterError(f"{name}: pinned artifact missing", "adapter.pin_mismatch")
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != self._pin.artifacts.get(name):
                raise AdapterError(f"{name}: SHA-256 {actual[:12]}… does not match the pin — refused", "adapter.pin_mismatch")
            self._verified[syntax] = path
        return self._verified[syntax]

    def rules(self) -> Iterable[Rule]:
        """Every assertion of the pinned artifacts: its id, its flag, its text — as CEN wrote them."""
        for syntax in sorted(self.syntaxes):
            root = ET.parse(self._artifact(syntax)).getroot()
            for fa in root.iter(SVRL + "failed-assert"):
                attrs = {a.get("name"): (a.text or "").strip() for a in fa.findall(XSL + "attribute")}
                text = fa.find(SVRL + "text")
                yield Rule(id=attrs["id"], severity=attrs.get("flag", "fatal"),
                           text=" ".join("".join(text.itertext()).split()) if text is not None else "")

    def accepts(self, path: str | Path) -> bool:
        return Path(path).suffix.lower() == ".xml"

    def findings(self, document: Any) -> Iterable[Finding]:
        path = Path(document)
        try:
            root = parse_xml(path)          # refuses a DOCTYPE: nothing in a check may reach the network
        except ValueError as e:
            raise AdapterError(str(e), "adapter.doctype_refused") from e
        except ET.ParseError as e:
            raise AdapterError(f"{path.name}: not well-formed XML ({e})", "einvoice.xml.malformed") from e
        syntax = syntax_of(root)
        if syntax not in self.syntaxes:
            raise AdapterError(f"{path.name}: not a UBL or CII invoice (root {root.tag})", "einvoice.syntax.unknown")
        if syntax not in self._compiled:
            xslt = _saxon().new_xslt30_processor()
            self._compiled[syntax] = xslt.compile_stylesheet(stylesheet_file=str(self._artifact(syntax)))
        svrl = self._compiled[syntax].transform_to_string(source_file=str(path.resolve()))
        if not svrl:
            raise AdapterError(f"{path.name}: Saxon returned no SVRL report", "adapter.engine_error")
        for fa in ET.fromstring(svrl.encode("utf-8")).iter(SVRL + "failed-assert"):
            text = fa.find(SVRL + "text")
            yield Finding(rule_id=fa.get("id", ""), severity=fa.get("flag", "fatal"),
                          message=" ".join("".join(text.itertext()).split()) if text is not None else "",
                          location=fa.get("location", ""), extra={"test": fa.get("test", ""), "syntax": syntax})


adapter = CenSchematron.from_manifest()
