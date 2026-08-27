import pdfplumber
import re


def extract_pdf_data(pdf_path):
    """
    Reads a Priority1 PDF and extracts the important fields.
    Returns a dictionary.
    """

    all_text = ""

    # -----------------------------
    # Read all text from the PDF
    # -----------------------------
    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                all_text += page_text + "\n"

    # -----------------------------
    # Invoice Number
    # -----------------------------
    invoice = re.search(r"Invoice\s+(\d+)", all_text)

    # -----------------------------
    # PO Number
    # Handles:
    # N111627
    # PO N111627
    # Customer PO N111627
    # -----------------------------
    po = re.search(r"\bN\d{6}\b", all_text)

    if not po:
        po = re.search(
            r"\bPO\s*[:#]?\s*([A-Z0-9\-]+)",
            all_text,
            re.IGNORECASE
        )

    if not po:
        po = re.search(
            r"\bCustomer\s+PO\s*[:#]?\s*([A-Z0-9\-]+)",
            all_text,
            re.IGNORECASE
        )

    # -----------------------------
    # Total Amount Due
    # -----------------------------
    price = re.search(
        r"Total Amount Due\s+USD\$([\d,]+\.\d{2})",
        all_text
    )

    # -----------------------------
    # Carrier
    # -----------------------------
    carrier = re.search(
        r"Carrier\s+([A-Za-z0-9 &\-\(\)\.]+?)\s+Description",
        all_text
    )

    # -----------------------------
    # Tracking Number (PRO)
    # -----------------------------
    tracking = re.search(
        r"PRO\s+(\d+)",
        all_text
    )

    # -----------------------------
    # BOL
    # -----------------------------
    bol = re.search(
        r"BOL\s+(\d+)",
        all_text
    )

    # -----------------------------
    # Return extracted values
    # -----------------------------
    return {
        "invoice_number": invoice.group(1) if invoice else None,

        "po": (
            po.group(0)
            if po and po.re.pattern == r"\bN\d{6}\b"
            else po.group(1) if po else None
        ),

        "price": (
            float(price.group(1).replace(",", ""))
            if price else None
        ),

        "carrier": (
            carrier.group(1).strip()
            if carrier else "Unknown"
        ),

        "tracking": (
            tracking.group(1)
            if tracking else None
        ),

        "bol": (
            bol.group(1)
            if bol else None
        )
    }