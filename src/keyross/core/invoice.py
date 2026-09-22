"""The canonical invoice: what invoice oracles reason about. EN 16931 business terms (BT-n), read from UBL or CII.

A second canonical model beside the tabular Document — one model per document family, Line in common. Standard library only."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keyross.core.document import Line

UBL_INVOICE = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
UBL_CREDIT_NOTE = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
CII = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"

NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "rsm": CII,
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}


@dataclass
class InvoiceLine(Line):
    """An invoice line (BG-25): the common Line (rid, number = BT-126, designation = BT-153, unit = BT-130, qty = BT-129,
    unit_price = BT-146, amount = BT-131) plus the line VAT (BT-151, BT-152)."""
    vat_category: str | None = None
    vat_rate: float | None = None


@dataclass
class VatBreakdown:
    """One VAT breakdown (BG-23)."""
    category: str                          # BT-118
    rate: float | None = None              # BT-119
    taxable_amount: float | None = None    # BT-116
    tax_amount: float | None = None        # BT-117
    exemption_reason: str | None = None    # BT-120
    exemption_code: str | None = None      # BT-121


@dataclass
class Totals:
    """Document totals (BG-22)."""
    line_net: float | None = None          # BT-106
    allowances: float | None = None        # BT-107
    charges: float | None = None           # BT-108
    tax_exclusive: float | None = None     # BT-109
    tax: float | None = None               # BT-110
    tax_inclusive: float | None = None     # BT-112
    prepaid: float | None = None           # BT-113
    rounding: float | None = None          # BT-114
    payable: float | None = None           # BT-115


@dataclass
class Party:
    name: str | None = None                # BT-27 / BT-44
    vat_id: str | None = None              # BT-31 / BT-48
    country: str | None = None             # BT-40 / BT-55


@dataclass
class Invoice:
    path: str
    syntax: str                            # "ubl" | "cii"
    number: str | None = None              # BT-1
    issue_date: str | None = None          # BT-2, ISO 8601 (YYYY-MM-DD)
    type_code: str | None = None           # BT-3
    currency: str | None = None            # BT-5
    seller: Party = field(default_factory=Party)
    buyer: Party = field(default_factory=Party)
    lines: list[InvoiceLine] = field(default_factory=list)
    vat: list[VatBreakdown] = field(default_factory=list)
    totals: Totals = field(default_factory=Totals)
    meta: dict[str, Any] = field(default_factory=dict)

    def amount_lines(self) -> list[InvoiceLine]:
        return list(self.lines)

    def row(self, rid: str) -> InvoiceLine | None:
        return next((l for l in self.lines if l.rid == rid), None)


def _num(v: str | None) -> float | None:
    if v is None or not v.strip():
        return None
    try:
        return float(v.strip())
    except ValueError:
        return None


def _txt(el: ET.Element | None, path: str) -> str | None:
    if el is None:
        return None
    found = el.find(path, NS)
    return found.text.strip() if found is not None and found.text is not None else None


def _cii_date(v: str | None) -> str | None:
    """CII dates use format 102 (YYYYMMDD); anything else is returned unchanged."""
    return f"{v[:4]}-{v[4:6]}-{v[6:8]}" if v and re.fullmatch(r"\d{8}", v) else v


def parse_xml(path: str | Path) -> ET.Element:
    """Parse an invoice file. A DOCTYPE is refused: external entities could reach the network or blow up memory."""
    data = Path(path).read_bytes()
    if re.search(rb"<!DOCTYPE", data, re.I):
        raise ValueError(f"{path}: document declares a DOCTYPE — refused")
    return ET.fromstring(data)


def syntax_of(root: ET.Element) -> str | None:
    ns = root.tag[1:].split("}")[0] if root.tag.startswith("{") else ""
    return "ubl" if ns in (UBL_INVOICE, UBL_CREDIT_NOTE) else ("cii" if ns == CII else None)


def load_invoice(path: str | Path) -> Invoice:
    """Load a UBL 2.1 or UN/CEFACT CII D16B invoice into the canonical Invoice."""
    root = parse_xml(path)
    syntax = syntax_of(root)
    if syntax == "ubl":
        return _load_ubl(str(path), root)
    if syntax == "cii":
        return _load_cii(str(path), root)
    raise ValueError(f"{path}: not an EN 16931 invoice (root {root.tag})")


def _ubl_party(party: ET.Element | None) -> Party:
    if party is None:
        return Party()
    vat = next((_txt(t, "cbc:CompanyID") for t in party.findall("cac:PartyTaxScheme", NS)
                if _txt(t, "cac:TaxScheme/cbc:ID") == "VAT"), None)
    return Party(name=_txt(party, "cac:PartyLegalEntity/cbc:RegistrationName") or _txt(party, "cac:PartyName/cbc:Name"),
                 vat_id=vat, country=_txt(party, "cac:PostalAddress/cac:Country/cbc:IdentificationCode"))


def _load_ubl(path: str, root: ET.Element) -> Invoice:
    credit = root.tag.endswith("}CreditNote")
    currency = _txt(root, "cbc:DocumentCurrencyCode")
    inv = Invoice(path=path, syntax="ubl", number=_txt(root, "cbc:ID"), issue_date=_txt(root, "cbc:IssueDate"),
                  type_code=_txt(root, "cbc:CreditNoteTypeCode" if credit else "cbc:InvoiceTypeCode"), currency=currency,
                  seller=_ubl_party(root.find("cac:AccountingSupplierParty/cac:Party", NS)),
                  buyer=_ubl_party(root.find("cac:AccountingCustomerParty/cac:Party", NS)))
    qty_tag = "cbc:CreditedQuantity" if credit else "cbc:InvoicedQuantity"
    for i, el in enumerate(root.findall("cac:CreditNoteLine" if credit else "cac:InvoiceLine", NS), start=1):
        lid = _txt(el, "cbc:ID") or str(i)
        q = el.find(qty_tag, NS)
        inv.lines.append(InvoiceLine(
            rid=f"rid:{lid}", row=i, number=lid, designation=_txt(el, "cac:Item/cbc:Name") or "",
            unit=q.get("unitCode") if q is not None else None, qty=_num(q.text if q is not None else None),
            unit_price=_num(_txt(el, "cac:Price/cbc:PriceAmount")), amount=_num(_txt(el, "cbc:LineExtensionAmount")),
            vat_category=_txt(el, "cac:Item/cac:ClassifiedTaxCategory/cbc:ID"),
            vat_rate=_num(_txt(el, "cac:Item/cac:ClassifiedTaxCategory/cbc:Percent"))))
    for tt in root.findall("cac:TaxTotal", NS):
        amount = tt.find("cbc:TaxAmount", NS)
        if amount is not None and amount.get("currencyID") in (None, currency):
            inv.totals.tax = _num(amount.text)
        for st in tt.findall("cac:TaxSubtotal", NS):
            inv.vat.append(VatBreakdown(
                category=_txt(st, "cac:TaxCategory/cbc:ID") or "", rate=_num(_txt(st, "cac:TaxCategory/cbc:Percent")),
                taxable_amount=_num(_txt(st, "cbc:TaxableAmount")), tax_amount=_num(_txt(st, "cbc:TaxAmount")),
                exemption_reason=_txt(st, "cac:TaxCategory/cbc:TaxExemptionReason"),
                exemption_code=_txt(st, "cac:TaxCategory/cbc:TaxExemptionReasonCode")))
    m = root.find("cac:LegalMonetaryTotal", NS)
    t = inv.totals
    t.line_net, t.tax_exclusive = _num(_txt(m, "cbc:LineExtensionAmount")), _num(_txt(m, "cbc:TaxExclusiveAmount"))
    t.tax_inclusive, t.allowances = _num(_txt(m, "cbc:TaxInclusiveAmount")), _num(_txt(m, "cbc:AllowanceTotalAmount"))
    t.charges, t.prepaid = _num(_txt(m, "cbc:ChargeTotalAmount")), _num(_txt(m, "cbc:PrepaidAmount"))
    t.rounding, t.payable = _num(_txt(m, "cbc:PayableRoundingAmount")), _num(_txt(m, "cbc:PayableAmount"))
    return inv


def _cii_party(party: ET.Element | None) -> Party:
    if party is None:
        return Party()
    vat = next((r.findtext("ram:ID", namespaces=NS) for r in party.findall("ram:SpecifiedTaxRegistration", NS)
                if (r.find("ram:ID", NS) is not None and r.find("ram:ID", NS).get("schemeID") == "VA")), None)
    return Party(name=_txt(party, "ram:Name"), vat_id=vat.strip() if vat else None,
                 country=_txt(party, "ram:PostalTradeAddress/ram:CountryID"))


def _load_cii(path: str, root: ET.Element) -> Invoice:
    trade = root.find("rsm:SupplyChainTradeTransaction", NS)
    agreement = trade.find("ram:ApplicableHeaderTradeAgreement", NS) if trade is not None else None
    settlement = trade.find("ram:ApplicableHeaderTradeSettlement", NS) if trade is not None else None
    currency = _txt(settlement, "ram:InvoiceCurrencyCode")
    inv = Invoice(path=path, syntax="cii", number=_txt(root, "rsm:ExchangedDocument/ram:ID"),
                  issue_date=_cii_date(_txt(root, "rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString")),
                  type_code=_txt(root, "rsm:ExchangedDocument/ram:TypeCode"), currency=currency,
                  seller=_cii_party(agreement.find("ram:SellerTradeParty", NS) if agreement is not None else None),
                  buyer=_cii_party(agreement.find("ram:BuyerTradeParty", NS) if agreement is not None else None))
    items = trade.findall("ram:IncludedSupplyChainTradeLineItem", NS) if trade is not None else []
    for i, el in enumerate(items, start=1):
        lid = _txt(el, "ram:AssociatedDocumentLineDocument/ram:LineID") or str(i)
        q = el.find("ram:SpecifiedLineTradeDelivery/ram:BilledQuantity", NS)
        tax = el.find("ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax", NS)
        inv.lines.append(InvoiceLine(
            rid=f"rid:{lid}", row=i, number=lid, designation=_txt(el, "ram:SpecifiedTradeProduct/ram:Name") or "",
            unit=q.get("unitCode") if q is not None else None, qty=_num(q.text if q is not None else None),
            unit_price=_num(_txt(el, "ram:SpecifiedLineTradeAgreement/ram:NetPriceProductTradePrice/ram:ChargeAmount")),
            amount=_num(_txt(el, "ram:SpecifiedLineTradeSettlement/ram:SpecifiedTradeSettlementLineMonetarySummation/ram:LineTotalAmount")),
            vat_category=_txt(tax, "ram:CategoryCode"), vat_rate=_num(_txt(tax, "ram:RateApplicablePercent"))))
    if settlement is not None:
        for tt in settlement.findall("ram:ApplicableTradeTax", NS):
            inv.vat.append(VatBreakdown(
                category=_txt(tt, "ram:CategoryCode") or "", rate=_num(_txt(tt, "ram:RateApplicablePercent")),
                taxable_amount=_num(_txt(tt, "ram:BasisAmount")), tax_amount=_num(_txt(tt, "ram:CalculatedAmount")),
                exemption_reason=_txt(tt, "ram:ExemptionReason"), exemption_code=_txt(tt, "ram:ExemptionReasonCode")))
        m = settlement.find("ram:SpecifiedTradeSettlementHeaderMonetarySummation", NS)
        t = inv.totals
        t.line_net, t.charges = _num(_txt(m, "ram:LineTotalAmount")), _num(_txt(m, "ram:ChargeTotalAmount"))
        t.allowances, t.tax_exclusive = _num(_txt(m, "ram:AllowanceTotalAmount")), _num(_txt(m, "ram:TaxBasisTotalAmount"))
        t.rounding, t.tax_inclusive = _num(_txt(m, "ram:RoundingAmount")), _num(_txt(m, "ram:GrandTotalAmount"))
        t.prepaid, t.payable = _num(_txt(m, "ram:TotalPrepaidAmount")), _num(_txt(m, "ram:DuePayableAmount"))
        if m is not None:
            for amount in m.findall("ram:TaxTotalAmount", NS):      # BT-110 is the one in the invoice currency (BT-111 is the other)
                if amount.get("currencyID") in (None, currency):
                    t.tax = _num(amount.text)
    return inv
