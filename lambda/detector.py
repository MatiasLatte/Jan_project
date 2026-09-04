import pdfplumber


def detect_invoice_type(pdf_path):
    """
    Detect the invoice type from PDF text.

    IMPORTANT:
    More specific carrier formats are checked before NASSAU
    because some R+L / Priority1 / carrier invoices contain
    Nassau National Cable information.
    """

    text = ""

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()

                if page_text:
                    text += page_text + "\n"

    except Exception as e:
        print(f"Detector PDF read error: {e}")
        return "UNKNOWN"

    text = text.upper()

    # ========================================================
    # R+L CARRIERS
    # ========================================================
    #
    # Examples:
    # R+L INV 2170292042601
    # R+L INV AJ18664562601
    # WEB PRO# WB9978426
    # WEB PRO# WC04108844
    # R+L'S DISCOUNT
    #
    # Check this BEFORE NASSAU because the invoice can contain
    # NASSAU NATIONAL CABLE as the customer.
    # ========================================================

    if (
        "R+L CARRIERS" in text
        or "R+L INV" in text
        or "R+L'S DISCOUNT" in text
        or "R+L'S" in text
        or "WEB PRO#" in text
        or "RLC5028" in text
    ):
        return "RL"

    # ========================================================
    # PRIORITY1
    # ========================================================

    if (
        "PRIORITY1" in text
        or "PRIORITY 1" in text
        or "PRIORITY ONE" in text
    ):
        return "PRIORITY1"

    # ========================================================
    # FEDEX
    # ========================================================

    if (
        "FEDEX" in text
        or "FEDERAL EXPRESS" in text
    ):
        return "FEDEX"

    # ========================================================
    # UPS
    # ========================================================

    if (
        "UNITED PARCEL SERVICE" in text
        or "UPS" in text
        or "1Z" in text
    ):
        return "UPS"

    # ========================================================
    # NASSAU NATIONAL CABLE
    # ========================================================

    if (
        "NASSAU NATIONAL CABLE" in text
        or "NASSAU NATIONAL" in text
    ):
        return "NASSAU"

    # ========================================================
    # UNKNOWN
    # ========================================================

    return "UNKNOWN"