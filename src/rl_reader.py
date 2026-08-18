import pdfplumber
import re


def extract_pdf_data(pdf_path):
    """
    Extract data from R+L Carrier invoices.
    """

    print("\n" + "=" * 70)
    print("R+L READER")
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
                print(repr(page_text))

            else:

                print("No text extracted from this page.")

    print("\n" + "=" * 70)
    print("Searching Fields")
    print("=" * 70)

    # -------------------------------------------------
    # Invoice Number
    # -------------------------------------------------

    invoice_patterns = [

        # Example: IAJ1866456
        r"\b(IAJ\d+)\b",

        # Example: Freight Bill No. IAJ1866456
        r"Freight\s*Bill\s*No\.?\s*(IAJ\d+)",

        # Example: R+L INV AJ18664562601
        r"R\+L\s*INV\s*(AJ\d+)",

        # Older format
        r"(I\d{9})",

        # Generic invoice formats
        r"Invoice\s*Number[:\s]*([A-Z0-9\-]+)",

        r"Invoice[:\s]*([A-Z0-9\-]+)"

    ]

    invoice = None

    for pattern in invoice_patterns:

        print(f"Trying Invoice Pattern : {pattern}")

        match = re.search(pattern, text, re.IGNORECASE)

        if match:

            invoice = match

            print(f"✅ Invoice Found : {match.group(1)}")

            break

    if invoice is None:

        print("❌ Invoice Number NOT FOUND")

    # -------------------------------------------------
    # Purchase Order
    # -------------------------------------------------

    po_patterns = [

       r"P\s*O\s*#\s*[:\-]?\s*([A-Z0-9]+)",

        r"Purchase\s*Order[:\s]*([A-Z0-9\-]+)",

        r"Customer\s*PO[:\s]*([A-Z0-9\-]+)",

        r"PO\s*Number[:\s]*([A-Z0-9\-]+)",

        r"Reference[:\s]*([A-Z0-9\-]+)",

        r"Ref\.?#?\s*2[:\s]*([A-Z0-9\-]+)"

    ]

    po = None

    for pattern in po_patterns:

        print(f"Trying PO Pattern : {pattern}")

        match = re.search(pattern, text, re.IGNORECASE)

        if match:

            po = match

            print(f"✅ PO Found : {match.group(1)}")

            break

    if po is None:

        print("\n❌ PO NOT FOUND")

    # -------------------------------------------------
    # Tracking Number
    # -------------------------------------------------

    tracking = re.search(

        r"WEB PRO#\s*([A-Z0-9]+)",

        text,

        re.IGNORECASE

    )

    if tracking:

        print(f"✅ Tracking : {tracking.group(1)}")

    else:

        print("❌ Tracking NOT FOUND")

    # -------------------------------------------------
    # Invoice Amount
    # -------------------------------------------------

    amounts = re.findall(r"\d+\.\d{2}", text)

    price = None

    if amounts:

        price = float(amounts[-1])

        print(f"✅ Invoice Amount : {price}")

    else:

        print("❌ Invoice Amount NOT FOUND")

    # -------------------------------------------------
    # Debug Output if PO Missing
    # -------------------------------------------------

    if po is None:

        print("\n" + "=" * 70)
        print("FIRST 2500 CHARACTERS OF EXTRACTED TEXT")
        print("=" * 70)

        print(text[:2500])

    # -------------------------------------------------
    # Return Data
    # -------------------------------------------------

    return {

        "invoice_number": invoice.group(1) if invoice else None,

        "po": po.group(1) if po else None,

        "price": price,

        "carrier": "R+L Carriers",

        "tracking": tracking.group(1) if tracking else None,

        "bol": None

    }