import pdfplumber
import re


def extract_all_text(pdf_path):
    """
    Extract text from all pages of a PDF.
    """

    all_text = []

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                all_text.append(page_text)

    return "\n".join(all_text)


def extract_invoice_number(text):
    """
    Extract Nassau invoice / pro forma invoice number.
    """

    patterns = [

        # PRO FORMA INVOICE #: NNC083126DIC
        r"PRO\s+FORMA\s+INVOICE\s*#\s*:?\s*([A-Z0-9\-]+)",

        # INVOICE #: 3121953
        r"INVOICE\s*#\s*:?\s*([A-Z0-9\-]+)",

        # INVOICE # 3121953
        r"INVOICE\s*#\s+([A-Z0-9\-]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            value = match.group(1).strip()

            # Prevent bad generic values.
            if value.upper() not in {
                "NUMBER",
                "FORM",
                "INVOICE"
            }:

                return value

    return None


def extract_customer_po(text):
    """
    Extract Nassau CUSTOMER PO.

    If the CUSTOMER PO field is blank, return None.

    IMPORTANT:
    Do not treat header words such as SALESPERSON,
    SHIP DATE, TRACKING, SHIP VIA, TERMS, etc.
    as a purchase order.
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for index, line in enumerate(lines):

        upper = line.upper()

        # Find the Nassau PO header
        if "CUSTOMER PO" not in upper:
            continue

        # The actual PO is normally on the following line.
        # Example:
        #
        # SALESPERSON CUSTOMER PO # SHIP DATE TRACKING SHIP VIA TERMS
        # SD 6705-631558 NET 30
        #
        # For a blank PO:
        #
        # SALESPERSON CUSTOMER PO # SHIP DATE TRACKING SHIP VIA TERMS
        # SD WIRE
        #
        if index + 1 >= len(lines):
            return None

        candidate = lines[index + 1].strip()

        if not candidate:
            return None

        # Remove known salesperson value at the beginning.
        candidate = re.sub(
            r"^SD\s+",
            "",
            candidate,
            flags=re.IGNORECASE
        ).strip()

        # These mean the PO field is blank.
        if candidate.upper() in {
            "WIRE",
            "PAID",
            "NET 30",
            "NET30",
            "SHIP DATE",
            "TRACKING",
            "SHIP VIA",
            "TERMS",
        }:
            return None

        # If the candidate is only a single digit,
        # it is almost certainly a line number.
        if re.fullmatch(r"\d", candidate):
            return None

        # If the candidate contains multiple fields,
        # take the first plausible PO-looking token.
        for token in candidate.split():

            token = token.strip(" ,:;|")

            if not token:
                continue

            if token.upper() in {
                "WIRE",
                "PAID",
                "SHIP",
                "DATE",
                "TRACKING",
                "SHIP",
                "VIA",
                "TERMS",
                "SALESPERSON",
            }:
                continue

            if re.fullmatch(r"\d", token):
                continue

            if len(token) >= 2:
                return token

        return None

    return None

    # ---------------------------------------------------------
    # First try the structured CUSTOMER PO section.
    # ---------------------------------------------------------

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for index, line in enumerate(lines):

        upper_line = line.upper()

        if "CUSTOMER PO #" in upper_line:

            # Look at the following few lines.
            nearby_lines = lines[index + 1:index + 4]

            for candidate in nearby_lines:

                candidate = candidate.strip()

                if not candidate:
                    continue

                # Remove common salesperson prefix.
                candidate = re.sub(
                    r"^[A-Z]{1,4}\s+",
                    "",
                    candidate
                )

                # First token is generally the PO.
                parts = candidate.split()

                if not parts:
                    continue

                possible_po = parts[0].strip()

                # Ignore obvious headers.
                if possible_po.upper() in {
                    "SHIP",
                    "SHIPDATE",
                    "TRACKING",
                    "WIRE",
                    "TERMS",
                    "NET",
                    "30",
                    "VIA"
                }:
                    continue

                # PO should contain at least one digit.
                if not re.search(r"\d", possible_po):
                    continue

                return possible_po

    # ---------------------------------------------------------
    # Fallback: search for PO label followed by value.
    # ---------------------------------------------------------

    patterns = [

        r"CUSTOMER\s+PO\s*#\s*:?\s*([A-Z0-9][A-Z0-9\-]*)",

        r"CUSTOMER\s+PO\s*:?\s*([A-Z0-9][A-Z0-9\-]*)",

        r"\bPO\s*#\s*:?\s*([A-Z0-9][A-Z0-9\-]*)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            value = match.group(1).strip()

            if value.upper() not in {
                "NUMBER",
                "FORM",
                "TERMS",
                "SHIP",
                "DATE"
            }:

                return value

    return None


def extract_invoice_total(text):
    """
    Extract the final Nassau invoice total.

    Nassau invoices typically contain:

        PRODUCT TOTAL DISCOUNT FREIGHT MISCELLANEOUS TAX INVOICE TOTAL
        $3,936.00 $373.92 $3,562.08

    The invoice total is the LAST monetary amount on the
    totals line.
    """

    lines = text.splitlines()

    for index, line in enumerate(lines):

        if "INVOICE TOTAL" not in line.upper():
            continue

        # -----------------------------------------------------
        # Check the following few lines for the totals.
        # -----------------------------------------------------

        search_lines = lines[index:index + 4]

        for search_line in search_lines:

            amounts = re.findall(
                r"\$?\s*([\d,]+\.\d{2})",
                search_line
            )

            if amounts:

                # The LAST amount is the INVOICE TOTAL.
                return float(
                    amounts[-1].replace(",", "")
                )

    return None   
    """
    Extract the Nassau invoice total.

    The Nassau documents contain:

        PRODUCT TOTAL DISCOUNT FREIGHT MISCELLANEOUS TAX INVOICE TOTAL

    followed by dollar amounts.

    We use the amount associated with INVOICE TOTAL.
    """

    # ---------------------------------------------------------
    # Try to find INVOICE TOTAL on the same/next line.
    # ---------------------------------------------------------

    match = re.search(
        r"INVOICE\s+TOTAL\s*(?:\n|\r\n)?\s*\$?\s*([\d,]+\.\d{2})",
        text,
        re.IGNORECASE
    )

    if match:

        return float(
            match.group(1).replace(",", "")
        )

    # ---------------------------------------------------------
    # Nassau PDFs sometimes place all totals on one line.
    #
    # Example:
    # PRODUCT TOTAL ... INVOICE TOTAL
    # $4,044.00 $0.00 ... $4,044.00
    #
    # In that case, take the final dollar amount on the
    # totals line.
    # ---------------------------------------------------------

    lines = text.splitlines()

    for index, line in enumerate(lines):

        if "INVOICE TOTAL" in line.upper():

            # Check this line and the next few lines.
            candidates = lines[index:index + 4]

            amounts = []

            for candidate in candidates:

                found = re.findall(
                    r"\$?\s*([\d,]+\.\d{2})",
                    candidate
                )

                amounts.extend(found)

            if amounts:

                return float(
                    amounts[-1].replace(",", "")
                )

    return None


def extract_customer(text):
    """
    Extract customer name from the BILL TO section.
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for index, line in enumerate(lines):

        if line.upper() == "BILL TO: SHIP TO:":

            candidates = lines[index + 1:index + 6]

            for candidate in candidates:

                if not candidate:
                    continue

                # Ignore obvious address/header information.
                if candidate.upper() in {
                    "UNITED STATES"
                }:
                    continue

                # Return the first useful customer/company line.
                return candidate

    return None


def extract_pdf_data(pdf_path):
    """
    Read a Nassau National Cable document and extract:

        invoice_number
        po
        price
        carrier
        tracking
        bol
        customer
    """

    text = extract_all_text(pdf_path)

    invoice_number = extract_invoice_number(text)

    po = extract_customer_po(text)

    price = extract_invoice_total(text)

    customer = extract_customer(text)

    return {
        "invoice_number": invoice_number,
        "po": po,
        "price": price,
        "carrier": "Nassau National Cable",
        "tracking": None,
        "bol": None,
        "customer": customer
    }
