"""Installed gauges. Importing a gauge registers its oracles; a dotted name (your own gauge) is imported as is."""
from __future__ import annotations

import importlib
from types import ModuleType


def load_gauge(name: str) -> ModuleType:
    """`load_gauge("einvoice")` imports keyross.gauges.einvoice; `load_gauge("mycompany.invoices")` imports that module."""
    return importlib.import_module(name if "." in name else f"keyross.gauges.{name}")
