import pdfplumber
import re


def extract_pdf_data(pdf_path):
    """
    Extract data from UPS invoices.
    """

    text = ""

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    # Invoice Number
    invoice = re.search(
        r"Invoice Number\s+([A-Z0-9]+)",
        text
    )

    # Tracking Number
    tracking = re.search(
        r"(1Z[A-Z0-9]{16})",
        text
    )

    # PO Number
    po = None

    patterns = [

        r"1st ref:\s*([A-Z]\d+)",
        r"2nd ref:\s*([A-Z]\d+)",

        r"1st ref:\s*(N\d+)",
        r"2nd ref:\s*(N\d+)",

        r"1st ref:\s*(E\d+)",
        r"2nd ref:\s*(E\d+)",

        r"1st ref:\s*(W\d+)",
        r"2nd ref:\s*(W\d+)"
    ]

    for pattern in patterns:

        match = re.search(pattern, text)

        if match:

            po = match.group(1)

            break

    # Total invoice amount

    price = re.search(
        r"Total Adjustments & Other Charges\s+([\d,]+\.\d{2})",
        text
    )

    if not price:

        price = re.search(
            r"TOTAL THIS INVOICE.*?([\d,]+\.\d{2})",
            text,
            re.DOTALL
        )

    return {

        "invoice_number":
            invoice.group(1) if invoice else None,

        "po":
            po,

        "price":
            float(price.group(1).replace(",", ""))
            if price else None,

        "carrier":
            "UPS",

        "tracking":
            tracking.group(1) if tracking else None,

        "bol":
            None
    }