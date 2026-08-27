import pdfplumber
import re


def extract_pdf_data(pdf_path):
    """Extract data from FedEx invoices with detailed debugging."""

    print("\n" + "=" * 70)
    print("FEDEX READER")
    print("=" * 70)

    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        print(f"Pages in PDF : {len(pdf.pages)}")

        for i, page in enumerate(pdf.pages, start=1):
            print(f"\nReading Page {i}")

            page_text = page.extract_text()

            if page_text:
                print(f"Characters Extracted : {len(page_text)}")
                text += page_text + "\n"
            else:
                print("No text found on this page.")

    print("\n")
    print("=" * 70)
    print("Searching Fields")
    print("=" * 70)

    print("\n" + "=" * 70)
    print("FULL EXTRACTED TEXT")
    print("=" * 70)
    print(text)

    # ---------------------------------------------------
    # Invoice Number
    # ---------------------------------------------------

    invoice = re.search(r"\b\d-\d{3}-\d{5}\b", text)

    if invoice:
        print(f"Invoice Number : {invoice.group(0)}")
    else:
        print("Invoice Number : NOT FOUND")

    # ---------------------------------------------------
    # PO Number (Old Layout)
    # ---------------------------------------------------

    po_patterns = [
        r"Ref\.\#2:\s*([A-Z0-9\-]+)",
        r"Ref\s*#2[:\s]*([A-Z0-9\-]+)",
        r"Reference\s*2[:\s]*([A-Z0-9\-]+)",
        r"Reference\s*#2[:\s]*([A-Z0-9\-]+)",
        r"Purchase Order[:\s]*([A-Z0-9\-]+)",
        r"\bPO\b[:\s#-]*([A-Z0-9\-]+)",
    ]

    po = None

    for pattern in po_patterns:

        print(f"\nTrying PO Pattern : {pattern}")

        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            po = match
            print(f"PO Found : {match.group(1)}")
            break

    # ---------------------------------------------------
    # New FedEx Shipment Layout
    # Recipient
    # NAME
    # N173967
    # ---------------------------------------------------

    if po is None:

     print("\nTrying shipment-detail PO extraction...")

    shipment_po = re.search(
        r"Recipient\s*\n\s*([^\n]+)\s*\n\s*([A-Z]\d+|N\d+[A-Z]?|E\d+|\d{7})",
        text,
        re.IGNORECASE,
    )

    if shipment_po:

        recipient_name = shipment_po.group(1).strip()
        po_value = shipment_po.group(2).strip()

        print(f"Recipient : {recipient_name}")
        print(f"Shipment PO Found : {po_value}")

        class DummyPO:
            def __init__(self, value):
                self.value = value

            def group(self, index):
                return self.value

        po = DummyPO(po_value)

    else:

        print("\nPO NOT FOUND")
        print(text[:2500])

    # ---------------------------------------------------
    # Recipient Charge
    # ---------------------------------------------------

    recipient_charge = None

    recipient_match = re.search(
        r"Recipient\s+.*?([0-9,]+\.\d{2})\s*$",
        text,
        re.MULTILINE,
    )

    if recipient_match:

        recipient_line = recipient_match.group(0)

        print(f"Recipient Line : {recipient_line}")

        numbers = re.findall(r"-?[0-9,]+\.\d{2}", recipient_line)

        if numbers:

            recipient_charge = float(numbers[-1].replace(",", ""))

            print(f"Recipient Charge : ${recipient_charge:.2f}")

    else:

        print("Recipient Charge : NOT FOUND")

    # ---------------------------------------------------
    # Tracking Number
    # ---------------------------------------------------

    tracking = re.search(r"Tracking ID\s+(\d+)", text)

    if tracking:

        print(f"Tracking : {tracking.group(1)}")

    else:

        print("Tracking : NOT FOUND")

    # ---------------------------------------------------
    # Invoice Amount
    # ---------------------------------------------------

    price = re.search(
        r"TOTAL THIS INVOICE USD \$([\d,]+\.\d{2})",
        text
    )

    if price:

        print(f"Invoice Amount : {price.group(1)}")

    else:

        print("Invoice Amount : NOT FOUND")

    return {
        "invoice_number": invoice.group(0) if invoice else None,
        "po": po.group(1) if po else None,
        "recipient_charge": recipient_charge,
        "price": float(price.group(1).replace(",", "")) if price else None,
        "carrier": "FedEx",
        "tracking": tracking.group(1) if tracking else None,
        "bol": None,
    }