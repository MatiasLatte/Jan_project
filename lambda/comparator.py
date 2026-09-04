def _to_float(value):
    """
    Safely convert a value to float.
    """
    if value is None:
        return None

    try:
        text = str(value).strip()

        if text.lower() in {
            "",
            "none",
            "null",
            "nan",
        }:
            return None

        text = (
            text
            .replace(",", "")
            .replace("$", "")
            .strip()
        )

        return float(text)

    except (ValueError, TypeError):
        return None


def _clean(value):
    """
    Safely convert a value to a normalized string.
    """
    if value is None:
        return ""

    text = str(value).strip()

    if text.lower() in {
        "",
        "none",
        "null",
        "nan",
    }:
        return ""

    return text


def _normalize_carrier(value):
    """
    Normalize carrier names for comparison.
    """
    text = _clean(value).upper()

    replacements = {
        "FEDEX": "FEDEX",
        "FED EX": "FEDEX",
        "FEDX": "FEDEX",

        "UPS": "UPS",

        "R+L CARRIERS": "RL",
        "R&L CARRIERS": "RL",
        "R + L CARRIERS": "RL",
        "R AND L CARRIERS": "RL",
        "R L CARRIERS": "RL",

        "CENTRAL TRANSPORT": "CENTRAL TRANSPORT",
        "ESTES": "ESTES",
        "NASSAU NATIONAL CABLE": "NASSAU",
    }

    for key, normalized in replacements.items():
        if key in text:
            return normalized

    return text


def _get_workbook_amount(workbook_data):
    """
    Determine the correct workbook amount.

    Individual Nassau Sales Invoice workbooks contain the
    actual invoice total / extended amount.

    Older Nassau master-workbook rows may instead contain
    Freight.

    Priority:
        1. Invoice Total
        2. Gross
        3. Extended
        4. Price
        5. Freight
    """

    amount_fields = [
        "Invoice Total",
        "InvoiceTotal",
        "Gross",
        "Gross Amount",
        "Extended",
        "Extended Amount",
        "Price",
        "Amount",
        "Freight",
    ]

    for field in amount_fields:

        value = _to_float(workbook_data.get(field))

        if value is not None:
            return value, field

    return None, None


def compare(pdf_data, workbook_data):
    """
    Compare PDF invoice data with workbook data.

    The workbook may come from either:
        - Nassau.xlsx
        - Individual Sales Invoice Excel files

    Price comparison uses the actual workbook invoice amount
    when available, rather than automatically comparing against
    Freight.
    """

    if workbook_data is None:
        return {
            "status": "PO NOT FOUND"
        }

    result = {}

    # =========================================================
    # PO
    # =========================================================

    pdf_po = _clean(pdf_data.get("po"))
    workbook_po = _clean(workbook_data.get("PO"))

    # ---------------------------------------------------------
    # Normal PO match
    # ---------------------------------------------------------

    result["po_match"] = (
        pdf_po.upper() == workbook_po.upper()
    )

    # ---------------------------------------------------------
    # Split-order PO support
    #
    # Example:
    # PDF:
    #     3121061A
    #
    # Workbook:
    #     3121061
    #
    # Split Order PO#:
    #     3121061A
    # ---------------------------------------------------------

    if not result["po_match"]:

        split_po = _clean(
            workbook_data.get("Split Order PO#")
        )

        if split_po:

            result["po_match"] = (
                pdf_po.upper() == split_po.upper()
            )

    # =========================================================
    # Carrier
    # =========================================================

    pdf_carrier = _normalize_carrier(
        pdf_data.get("carrier")
    )

    workbook_carrier = _normalize_carrier(
        workbook_data.get("Carrier")
    )

    if not pdf_carrier or not workbook_carrier:

        result["carrier_match"] = True

    else:

        result["carrier_match"] = (
            pdf_carrier == workbook_carrier
            or pdf_carrier in workbook_carrier
            or workbook_carrier in pdf_carrier
        )

    # =========================================================
    # Tracking
    # =========================================================

    workbook_tracking = (
        workbook_data.get("Tracking Number")
        or workbook_data.get("Tracking")
        or workbook_data.get("Tracing Number")
        or workbook_data.get("PRO")
        or ""
    )

    pdf_tracking = _clean(
        pdf_data.get("tracking")
    )

    workbook_tracking = _clean(
        workbook_tracking
    )

    if not pdf_tracking or not workbook_tracking:

        result["tracking_match"] = True

    else:

        result["tracking_match"] = (
            pdf_tracking.upper()
            ==
            workbook_tracking.upper()
        )

    # =========================================================
    # BOL
    # =========================================================

    workbook_bol = (
        workbook_data.get("BOL")
        or workbook_data.get("Person Submitting")
        or ""
    )

    pdf_bol = _clean(
        pdf_data.get("bol")
    )

    workbook_bol = _clean(
        workbook_bol
    )

    if not pdf_bol or not workbook_bol:

        result["bol_match"] = True

    else:

        result["bol_match"] = (
            pdf_bol.upper()
            ==
            workbook_bol.upper()
        )

    # =========================================================
    # WORKBOOK AMOUNT
    # =========================================================

    workbook_amount, workbook_amount_field = (
        _get_workbook_amount(workbook_data)
    )

    # =========================================================
    # PDF AMOUNT
    # =========================================================

    # FedEx invoices use Recipient Charge when available.
    # Other carriers use the extracted invoice price.
    # =========================================================

    if pdf_carrier == "FEDEX":

        pdf_amount = _to_float(
            pdf_data.get("recipient_charge")
        )

        if pdf_amount is None:
            pdf_amount = _to_float(
                pdf_data.get("price")
            )

    else:

        pdf_amount = _to_float(
            pdf_data.get("price")
        )

    # =========================================================
    # PRICE COMPARISON
    # =========================================================

    result["pdf_price"] = (
        pdf_amount if pdf_amount is not None else 0.0
    )

    result["workbook_amount"] = (
        workbook_amount
        if workbook_amount is not None
        else 0.0
    )

    # Keep these fields for compatibility with the existing
    # report generator / processor.
    result["workbook_freight"] = _to_float(
        workbook_data.get("Freight")
    ) or 0.0

    result["workbook_amount_field"] = (
        workbook_amount_field
    )

    if (
        pdf_amount is None
        or workbook_amount is None
    ):

        result["price_difference"] = None
        result["price_match"] = True

    else:

        result["price_difference"] = round(
            abs(pdf_amount - workbook_amount),
            2
        )

        result["price_match"] = (
            result["price_difference"] == 0
        )

    # =========================================================
    # OVERALL RESULT
    # =========================================================

    result["status"] = (
        "MATCH"
        if (
            result["po_match"]
            and result["carrier_match"]
            and result["tracking_match"]
            and result["bol_match"]
            and result["price_match"]
        )
        else "MISMATCH"
    )

    return result