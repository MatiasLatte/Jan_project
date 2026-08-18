def compare(pdf_data, workbook_data):
    """
    Compare PDF data with workbook data.
    Works across different workbook sheets.
    """

    if workbook_data is None:
        return {
            "status": "PO NOT FOUND"
        }

    result = {}

    # -----------------------------
    # PO
    # -----------------------------
    result["po_match"] = (
        str(pdf_data.get("po", "")).strip()
        ==
        str(workbook_data.get("PO", "")).strip()
    )

    # -----------------------------
    # Carrier
    # -----------------------------
    pdf_carrier = str(pdf_data.get("carrier", "")).upper()
    workbook_carrier = str(workbook_data.get("Carrier", "")).upper()

    result["carrier_match"] = (
        workbook_carrier in pdf_carrier
        or pdf_carrier in workbook_carrier
    )

    # -----------------------------
    # Tracking
    # -----------------------------
    workbook_tracking = (
        workbook_data.get("Tracking Number")
        or workbook_data.get("Tracking")
        or workbook_data.get("PRO")
        or ""
    )

    result["tracking_match"] = (
        str(pdf_data.get("tracking", "")).strip()
        ==
        str(workbook_tracking).strip()
    )

    # -----------------------------
    # BOL
    # -----------------------------
    workbook_bol = (
        workbook_data.get("Person Submitting")
        or workbook_data.get("BOL")
        or ""
    )

    result["bol_match"] = (
        str(pdf_data.get("bol", "")).strip()
        ==
        str(workbook_bol).strip()
    )

    # -----------------------------
    # Freight
    # -----------------------------
    try:
        workbook_freight = float(workbook_data.get("Freight", 0))
    except:
        workbook_freight = 0.0

    # -------------------------------------------------
    # FedEx uses Recipient Charge
    # All other carriers use Invoice Total
    # -------------------------------------------------
    if pdf_carrier == "FEDEX":

        pdf_amount = pdf_data.get("recipient_charge")

        if pdf_amount is None:
            pdf_amount = pdf_data.get("price", 0)

    else:

        pdf_amount = pdf_data.get("price", 0)

    result["pdf_price"] = float(pdf_amount)
    result["workbook_freight"] = workbook_freight
    result["price_difference"] = round(
    abs(result["pdf_price"] - result["workbook_freight"]),
    2
)

    result["price_match"] = result["price_difference"] == 0

    return result