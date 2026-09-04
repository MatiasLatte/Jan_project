import pdfplumber
import re


def extract_pdf_data(pdf_path):
    """
    Reads an R+L Carriers invoice and extracts important fields.
    Returns a dictionary.
    """

    all_text = ""

    # ============================================================
    # READ PDF
    # ============================================================

    try:

        with pdfplumber.open(pdf_path) as pdf:

            for page in pdf.pages:

                page_text = page.extract_text()

                if page_text:
                    all_text += page_text + "\n"

    except Exception as e:

        print(f"R+L PDF read error: {e}")

        return {
            "invoice_number": None,
            "po": None,
            "price": None,
            "carrier": "R+L Carriers",
            "tracking": None,
            "bol": None,
            "customer": None
        }

    # ============================================================
    # NORMALIZE TEXT
    # ============================================================

    text = all_text.upper()

    # ============================================================
    # INVOICE NUMBER
    #
    # Examples:
    # R+L INV 2170292042601
    # R+L INV AJ18664562601
    # ============================================================

    invoice = re.search(
        r"R\+L\s+INV\s*[:#]?\s*([A-Z0-9]+)",
        text
    )

    # ============================================================
    # PO NUMBER
    #
    # Important:
    # R+L PDFs can contain:
    #
    # P O # 3121061A
    # PO # 3121061A
    # PO 3121061A
    #
    # We specifically look for the PO label instead of using
    # a broad pattern that can accidentally capture other text.
    # ============================================================

    po = None

    # First priority: exact "P O #" format
    po_match = re.search(
        r"\bP\s+O\s*#\s*([A-Z0-9][A-Z0-9\-]*)\b",
        text
    )

    if po_match:
        po = po_match.group(1).strip()

    # Second: "P O" without #
    if not po:

        po_match = re.search(
            r"\bP\s+O\s+([A-Z0-9][A-Z0-9\-]*)\b",
            text
        )

        if po_match:
            po = po_match.group(1).strip()

    # Third: normal "PO #"
    if not po:

        po_match = re.search(
            r"\bPO\s*#\s*([A-Z0-9][A-Z0-9\-]*)\b",
            text
        )

        if po_match:
            po = po_match.group(1).strip()

    # Fourth: normal "PO"
    if not po:

        po_match = re.search(
            r"\bPO\s+([A-Z0-9][A-Z0-9\-]*)\b",
            text
        )

        if po_match:
            po = po_match.group(1).strip()

    # ============================================================
    # SHIPPER NUMBER
    # ============================================================

    shipper = re.search(
        r"SHIPPER#\s*([A-Z0-9\-]+)",
        text
    )

    # ============================================================
    # WEB PRO / TRACKING
    #
    # Examples:
    # WEB PRO# WB9978426
    # WEB PRO# WC04108844
    # ============================================================

    tracking = re.search(
        r"WEB\s+PRO#\s*([A-Z0-9\-]+)",
        text
    )

    # ============================================================
    # BOL
    #
    # Example:
    # R11 BOL POD
    # ============================================================

    bol = re.search(
        r"\bBOL\s+([A-Z0-9\-]+)",
        text
    )

    # ============================================================
    # PRICE
    #
    # R+L invoice header:
    #
    # NAS215 07/08/26 I217029204 $231.72
    #
    # The amount immediately following the invoice number is
    # the invoice total in these samples.
    # ============================================================

    price = re.search(
        r"NAS\d+\s+\d{2}/\d{2}/\d{2}\s+"
        r"[A-Z0-9]+\s+\$?\s*([\d,]+\.\d{2})",
        text
    )

    # Fallback: first dollar amount
    if not price:

        price = re.search(
            r"\$\s*([\d,]+\.\d{2})",
            text
        )

    # ============================================================
    # CUSTOMER
    # ============================================================

    customer = None

    # ============================================================
    # RETURN DATA
    # ============================================================

    return {

        "invoice_number": (
            invoice.group(1).strip()
            if invoice
            else None
        ),

        "po": po,

        "price": (
            float(
                price.group(1).replace(",", "")
            )
            if price
            else None
        ),

        "carrier": "R+L Carriers",

        "tracking": (
            tracking.group(1).strip()
            if tracking
            else None
        ),

        "bol": (
            bol.group(1).strip()
            if bol
            else None
        ),

        "customer": customer
    }