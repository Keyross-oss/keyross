"""Gauge einvoice — EN 16931 e-invoices (UBL, CII): the official CEN Schematron, executed as published, no rule rewritten;
and the delta oracles, which check the invoice against its order (ctx["order"]). Importing this module registers the
adapter, one registry entry per rule id of the pinned release, and the delta oracles."""
from keyross.gauges.einvoice.adapters.schematron import adapter
from keyross.gauges.einvoice import oracles as _oracles  # noqa: F401 — the delta oracles: the invoice against its order

adapter.register()
