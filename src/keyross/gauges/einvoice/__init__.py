"""Gauge einvoice — EN 16931 e-invoices (UBL, CII): the official CEN Schematron, executed as published; no rule rewritten.
Importing this module registers the adapter and one registry entry per rule id of the pinned release."""
from keyross.gauges.einvoice.adapters.schematron import adapter

adapter.register()
