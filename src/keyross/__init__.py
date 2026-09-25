"""Keyross — a compiler for your agent's outputs.

An oracle is a pure function (document, context) -> Verdict. Deterministic or nothing.
"""
from keyross.core.verdict import Verdict, Severity, Status
from keyross.core.registry import oracle, contract, registry
from keyross.core.document import Document, Line, load
from keyross.core.invoice import Invoice, InvoiceLine, load_invoice
from keyross.core.runner import run, Report

__version__ = "0.1.1"
__all__ = ["Verdict", "Severity", "Status", "oracle", "contract", "registry", "Document", "Line", "load", "Invoice", "InvoiceLine", "load_invoice", "run", "Report"]
