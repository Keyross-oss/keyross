"""The reference invoice of an order, in UN/CEFACT CII D16B (the XML of Factur-X, profile EN 16931).

It proves each task is solvable: every reference must pass the official CEN rules with no fatal finding and match its order
(`python -m bench.einvoice.reference` checks the 20). It is also what the offline scripted model writes."""
from __future__ import annotations

from xml.sax.saxutils import escape

from bench.einvoice.orders import expected

NS = ('xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" '
      'xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100" '
      'xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"')


def _date(iso: str) -> str:
    return f'<udt:DateTimeString format="102">{iso.replace("-", "")}</udt:DateTimeString>'


def _party(tag: str, p: dict) -> str:
    a = p["address"]
    return (f"<ram:{tag}><ram:Name>{escape(p['name'])}</ram:Name>"
            f"<ram:PostalTradeAddress><ram:PostcodeCode>{a['postcode']}</ram:PostcodeCode><ram:LineOne>{escape(a['line'])}</ram:LineOne>"
            f"<ram:CityName>{escape(a['city'])}</ram:CityName><ram:CountryID>{a['country']}</ram:CountryID></ram:PostalTradeAddress>"
            f"<ram:SpecifiedTaxRegistration><ram:ID schemeID=\"VA\">{p['vat_id']}</ram:ID></ram:SpecifiedTaxRegistration></ram:{tag}>")


def _tax(category: str, rate: str) -> str:
    return f"<ram:TypeCode>VAT</ram:TypeCode><ram:CategoryCode>{category}</ram:CategoryCode><ram:RateApplicablePercent>{rate}</ram:RateApplicablePercent>"


def to_cii(order: dict, *, line_total_shift: str | None = None) -> str:
    """The reference invoice. `line_total_shift` corrupts BT-106 (the sum of line net amounts) — the scripted model's draft."""
    inv, exp = order["invoice"], expected(order)
    cur = inv["currency"]
    lines = "".join(
        "<ram:IncludedSupplyChainTradeLineItem>"
        f"<ram:AssociatedDocumentLineDocument><ram:LineID>{l['id']}</ram:LineID></ram:AssociatedDocumentLineDocument>"
        f"<ram:SpecifiedTradeProduct><ram:Name>{escape(l['name'])}</ram:Name></ram:SpecifiedTradeProduct>"
        f"<ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice><ram:ChargeAmount>{l['net_price']}</ram:ChargeAmount>"
        "</ram:NetPriceProductTradePrice></ram:SpecifiedLineTradeAgreement>"
        f"<ram:SpecifiedLineTradeDelivery><ram:BilledQuantity unitCode=\"{l['unit_code']}\">{l['quantity']}</ram:BilledQuantity></ram:SpecifiedLineTradeDelivery>"
        f"<ram:SpecifiedLineTradeSettlement><ram:ApplicableTradeTax>{_tax(l['vat_category'], l['vat_rate'])}</ram:ApplicableTradeTax>"
        f"<ram:SpecifiedTradeSettlementLineMonetarySummation><ram:LineTotalAmount>{exp['line_net'][l['id']]}</ram:LineTotalAmount>"
        "</ram:SpecifiedTradeSettlementLineMonetarySummation></ram:SpecifiedLineTradeSettlement>"
        "</ram:IncludedSupplyChainTradeLineItem>"
        for l in order["lines"])
    delivery = ""
    if order.get("delivery"):
        d = order["delivery"]
        delivery = (f"<ram:ShipToTradeParty><ram:PostalTradeAddress><ram:CountryID>{d['country']}</ram:CountryID></ram:PostalTradeAddress></ram:ShipToTradeParty>"
                    f"<ram:ActualDeliverySupplyChainEvent><ram:OccurrenceDateTime>{_date(d['date'])}</ram:OccurrenceDateTime></ram:ActualDeliverySupplyChainEvent>")
    breakdown = ""
    for key, v in exp["vat"].items():
        category, rate = key.split()
        ex = order["vat_exemptions"].get(category)
        breakdown += (f"<ram:ApplicableTradeTax><ram:CalculatedAmount>{v['tax']}</ram:CalculatedAmount><ram:TypeCode>VAT</ram:TypeCode>"
                      + (f"<ram:ExemptionReason>{escape(ex['reason'])}</ram:ExemptionReason>" if ex else "")
                      + f"<ram:BasisAmount>{v['taxable']}</ram:BasisAmount><ram:CategoryCode>{category}</ram:CategoryCode>"
                      + (f"<ram:ExemptionReasonCode>{ex['code']}</ram:ExemptionReasonCode>" if ex else "")
                      + f"<ram:RateApplicablePercent>{rate}</ram:RateApplicablePercent></ram:ApplicableTradeTax>")
    adjustments = "".join(
        f"<ram:SpecifiedTradeAllowanceCharge><ram:ChargeIndicator><udt:Indicator>{'true' if charge else 'false'}</udt:Indicator></ram:ChargeIndicator>"
        f"<ram:ActualAmount>{x['amount']}</ram:ActualAmount><ram:Reason>{escape(x['reason'])}</ram:Reason>"
        f"<ram:CategoryTradeTax>{_tax(x['vat_category'], x['vat_rate'])}</ram:CategoryTradeTax></ram:SpecifiedTradeAllowanceCharge>"
        for charge, xs in ((False, order["allowances"]), (True, order["charges"])) for x in xs)
    line_total = exp["line_total"] if line_total_shift is None else f"{float(exp['line_total']) + float(line_total_shift):.2f}"
    totals = (f"<ram:LineTotalAmount>{line_total}</ram:LineTotalAmount>"
              + (f"<ram:ChargeTotalAmount>{exp['charges']}</ram:ChargeTotalAmount>" if order["charges"] else "")
              + (f"<ram:AllowanceTotalAmount>{exp['allowances']}</ram:AllowanceTotalAmount>" if order["allowances"] else "")
              + f"<ram:TaxBasisTotalAmount>{exp['tax_exclusive']}</ram:TaxBasisTotalAmount>"
              + f"<ram:TaxTotalAmount currencyID=\"{cur}\">{exp['tax']}</ram:TaxTotalAmount>"
              + f"<ram:GrandTotalAmount>{exp['tax_inclusive']}</ram:GrandTotalAmount><ram:DuePayableAmount>{exp['payable']}</ram:DuePayableAmount>")
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<rsm:CrossIndustryInvoice {NS}>'
            "<rsm:ExchangedDocumentContext><ram:GuidelineSpecifiedDocumentContextParameter><ram:ID>urn:cen.eu:en16931:2017</ram:ID>"
            "</ram:GuidelineSpecifiedDocumentContextParameter></rsm:ExchangedDocumentContext>"
            f"<rsm:ExchangedDocument><ram:ID>{inv['number']}</ram:ID><ram:TypeCode>{inv['type_code']}</ram:TypeCode>"
            f"<ram:IssueDateTime>{_date(inv['issue_date'])}</ram:IssueDateTime></rsm:ExchangedDocument>"
            f"<rsm:SupplyChainTradeTransaction>{lines}"
            f"<ram:ApplicableHeaderTradeAgreement><ram:BuyerReference>{inv['buyer_reference']}</ram:BuyerReference>"
            f"{_party('SellerTradeParty', order['seller'])}{_party('BuyerTradeParty', order['buyer'])}</ram:ApplicableHeaderTradeAgreement>"
            f"<ram:ApplicableHeaderTradeDelivery>{delivery}</ram:ApplicableHeaderTradeDelivery>"
            f"<ram:ApplicableHeaderTradeSettlement><ram:InvoiceCurrencyCode>{cur}</ram:InvoiceCurrencyCode>"
            f"<ram:SpecifiedTradeSettlementPaymentMeans><ram:TypeCode>{order['payment']['means_code']}</ram:TypeCode>"
            f"<ram:PayeePartyCreditorFinancialAccount><ram:IBANID>{order['payment']['iban']}</ram:IBANID></ram:PayeePartyCreditorFinancialAccount>"
            f"</ram:SpecifiedTradeSettlementPaymentMeans>{breakdown}{adjustments}"
            f"<ram:SpecifiedTradePaymentTerms><ram:DueDateDateTime>{_date(inv['due_date'])}</ram:DueDateDateTime></ram:SpecifiedTradePaymentTerms>"
            f"<ram:SpecifiedTradeSettlementHeaderMonetarySummation>{totals}</ram:SpecifiedTradeSettlementHeaderMonetarySummation>"
            "</ram:ApplicableHeaderTradeSettlement></rsm:SupplyChainTradeTransaction></rsm:CrossIndustryInvoice>\n")
