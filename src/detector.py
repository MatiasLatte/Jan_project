import pdfplumber


def detect_invoice_type(pdf_path):
    """
    Detect which carrier generated the invoice.
    """

    text = ""

    with pdfplumber.open(pdf_path) as pdf:

        first_page = pdf.pages[0].extract_text()

        if first_page:
            text = first_page

    text = text.upper()

    # Priority1
    if "PRIORITY1" in text:
        return "PRIORITY1"

    # R+L Carriers
    if "R+L" in text or "R & L" in text or "R+L CARRIERS" in text or "RL CARRIERS" in text:
        return "RL"

    # FedEx
    if "FEDEX" in text:
        return "FEDEX"

    # UPS
    if "UPS" in text:
        return "UPS"
    
      # Unknown
    return "UNKNOWN"