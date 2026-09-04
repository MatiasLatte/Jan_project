import os
import csv
import re
import math

from detector import detect_invoice_type
from workbook_reader import find_po, search_tracking

from priority1_reader import extract_pdf_data as priority1_reader
from nassau_reader import extract_pdf_data as nassau_reader
from rl_reader import extract_pdf_data as rl_reader

try:
    from fedex_reader import extract_pdf_data as fedex_reader
except ImportError:
    fedex_reader = None

try:
    from ups_reader import extract_pdf_data as ups_reader
except ImportError:
    ups_reader = None


DEFAULT_QUEUE_FOLDER = "/tmp/jan_project/queue"
DEFAULT_OUTPUT_FOLDER = "/tmp/jan_project/output"


# ============================================================
# INVALID VALUES
# ============================================================

INVALID_VALUES = {
    "",
    "NONE",
    "NULL",
    "NAN",
    "NA",
    "N/A",
    "P O",
    "PO",
    "FORM",
    "NUMBER",
    "INVOICE",
    "TERMS",
    "ID",
    "UNKNOWN",
    "SALESPERSON",
    "SHIP",
    "DATE",
    "POD",
    "BOL",
    "PRO",
    "TRACKING",
    "TRACKING NUMBER",
    "CUSTOMER",
    "NAME",
    "ADDRESS",
}


# ============================================================
# VALUE CLEANING
# ============================================================

def clean_value(value):
    """
    Clean a generic value.

    Converts obvious empty/invalid values to None.
    Also rejects NaN and infinite numeric values.
    """

    if value is None:
        return None

    try:
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
    except Exception:
        pass

    try:
        text = str(value).strip()
    except Exception:
        return None

    if not text:
        return None

    if text.upper() in INVALID_VALUES:
        return None

    if text.lower() in {
        "nan",
        "none",
        "null",
        "n/a",
        "na",
    }:
        return None

    return text


def clean_po(value):
    """
    Clean PO value.

    Rejects obvious false PO extractions.
    """

    value = clean_value(value)

    if not value:
        return None

    # A PO must contain at least one number.
    if not any(ch.isdigit() for ch in value):
        return None

    return value


# ============================================================
# IDENTIFIER NORMALIZATION
# ============================================================

def normalize_identifier(value):
    """
    Normalize an identifier for comparison.

    Examples:

        N173009      -> N173009
        n-173009    -> N173009
        3121061-A    -> 3121061A
        I217029204   -> I217029204
    """

    value = clean_value(value)

    if not value:
        return None

    text = str(value).upper().strip()

    # Remove spaces, punctuation and separators.
    text = re.sub(
        r"[^A-Z0-9]",
        "",
        text
    )

    if not text:
        return None

    return text


def normalize_po(value):
    """
    Normalize a PO specifically.
    """

    value = clean_po(value)

    if not value:
        return None

    return normalize_identifier(value)


def normalize_tracking(value):
    """
    Normalize tracking number.
    """

    value = clean_value(value)

    if not value:
        return None

    return normalize_identifier(value)


def normalize_bol(value):
    """
    Normalize BOL.

    Rejects generic words such as POD/BOL.
    """

    value = clean_value(value)

    if not value:
        return None

    normalized = normalize_identifier(value)

    if not normalized:
        return None

    if normalized in {
        "POD",
        "BOL",
        "PRO",
        "TRACKING",
        "TRACKINGNUMBER",
        "SALESPERSON",
    }:
        return None

    # A BOL should contain at least one digit.
    if not any(ch.isdigit() for ch in normalized):
        return None

    return normalized


def normalize_invoice_number(value):
    """
    Normalize invoice number.
    """

    value = clean_value(value)

    if not value:
        return None

    return normalize_identifier(value)


# ============================================================
# READER SELECTION
# ============================================================

def get_reader(invoice_type):
    """
    Return the correct PDF reader.
    """

    readers = {
        "NASSAU": nassau_reader,
        "PRIORITY1": priority1_reader,
        "RL": rl_reader,
        "FEDEX": fedex_reader,
        "UPS": ups_reader,
    }

    return readers.get(invoice_type)


# ============================================================
# WORKBOOK VALUE
# ============================================================

def get_workbook_value(
    row,
    *keys
):
    """
    Safely retrieve a workbook value.

    Supports exact and case-insensitive keys.
    """

    if not row:
        return None

    if not isinstance(row, dict):
        return None

    for key in keys:

        # Exact key
        try:

            if key in row:

                value = row.get(key)

                if value is not None:
                    return value

        except Exception:
            pass

        # Case-insensitive key
        try:

            requested_key = (
                str(key)
                .strip()
                .upper()
            )

            for actual_key, value in row.items():

                actual_key_clean = (
                    str(actual_key)
                    .strip()
                    .upper()
                )

                if (
                    actual_key_clean
                    == requested_key
                ):

                    if value is not None:
                        return value

        except Exception:
            pass

    return None


# ============================================================
# ROW IDENTIFIERS
# ============================================================

def get_row_po(row):
    return get_workbook_value(
        row,
        "PO",
        "Purchase Order",
        "PO Number",
        "Order",
        "Order Number",
    )


def get_row_tracking(row):
    return get_workbook_value(
        row,
        "Tracing Number",
        "Tracking Number",
        "Tracking",
        "PRO",
        "Pro Number",
        "PRO Number",
    )


def get_row_bol(row):
    return get_workbook_value(
        row,
        "BOL",
        "BOL Number",
        "Bill of Lading",
        "Bill Of Lading",
    )


def get_row_invoice(row):
    return get_workbook_value(
        row,
        "Invoice",
        "Invoice Number",
        "Invoice #",
    )


# ============================================================
# ROW VALIDATION
# ============================================================

def row_matches_po(
    row,
    requested_po
):
    """
    Validate that a workbook result really belongs
    to the requested PO.
    """

    requested = normalize_po(
        requested_po
    )

    if not requested:
        return False

    workbook_po = normalize_po(
        get_row_po(row)
    )

    if not workbook_po:
        return False

    # Exact normalized match.
    if workbook_po == requested:
        return True

    # Split PO support.
    requested_base = extract_base_po(
        requested
    )

    workbook_base = extract_base_po(
        workbook_po
    )

    if requested_base:

        if workbook_po == requested_base:
            return True

    if workbook_base:

        if workbook_base == requested:
            return True

    if requested_base and workbook_base:

        if requested_base == workbook_base:
            return True

    return False


def row_matches_tracking(
    row,
    requested_tracking
):
    """
    Validate tracking search result.
    """

    requested = normalize_tracking(
        requested_tracking
    )

    if not requested:
        return False

    workbook_tracking = normalize_tracking(
        get_row_tracking(row)
    )

    if not workbook_tracking:
        return False

    return (
        workbook_tracking
        == requested
    )


def row_matches_bol(
    row,
    requested_bol
):
    """
    Validate BOL search result.

    This prevents a search result caused by
    generic text such as POD from being accepted.
    """

    requested = normalize_bol(
        requested_bol
    )

    if not requested:
        return False

    workbook_bol = normalize_bol(
        get_row_bol(row)
    )

    if not workbook_bol:
        return False

    return (
        workbook_bol
        == requested
    )


def row_matches_invoice(
    row,
    requested_invoice
):
    """
    Validate invoice-number search result.
    """

    requested = normalize_invoice_number(
        requested_invoice
    )

    if not requested:
        return False

    workbook_invoice = normalize_invoice_number(
        get_row_invoice(row)
    )

    if not workbook_invoice:
        return False

    return (
        workbook_invoice
        == requested
    )


# ============================================================
# WORKBOOK SEARCH HELPERS
# ============================================================

def try_workbook_search(
    value,
    validate=True
):
    """
    Search workbook by PO.

    Multiple representations are attempted.
    Every returned row is validated before accepting it.
    """

    value = clean_po(value)

    if not value:
        return None

    variants = []

    def add_variant(v):
        if not v:
            return

        if v not in variants:
            variants.append(v)

    add_variant(value)

    normalized = normalize_po(value)

    if normalized:
        add_variant(normalized)

    # Original base PO.
    base = extract_base_po(
        value
    )

    if base:
        add_variant(base)

    normalized_base = extract_base_po(
        normalized
    )

    if normalized_base:
        add_variant(normalized_base)

    for variant in variants:

        try:

            print(
                f"Trying workbook PO: "
                f"{variant}"
            )

            row = find_po(
                variant
            )

            if not row:
                continue

            if not validate:
                return row

            if row_matches_po(
                row,
                value
            ):

                print(
                    "Validated workbook PO "
                    f"match: {variant}"
                )

                return row

            print(
                "Rejected workbook PO "
                "candidate because returned "
                "row PO does not match."
            )

        except Exception as e:

            print(
                f"Workbook PO search error "
                f"for {variant}: {e}"
            )

    return None


def try_tracking_search(
    value,
    validate=True
):
    """
    Search workbook by tracking.

    The returned row is validated against the
    actual tracking number.
    """

    value = clean_value(value)

    if not value:
        return None

    variants = []

    def add_variant(v):
        if not v:
            return

        if v not in variants:
            variants.append(v)

    add_variant(value)

    normalized = normalize_tracking(
        value
    )

    if normalized:
        add_variant(normalized)

    for variant in variants:

        try:

            print(
                f"Trying workbook tracking: "
                f"{variant}"
            )

            row = search_tracking(
                variant
            )

            if not row:
                continue

            if not validate:
                return row

            if row_matches_tracking(
                row,
                value
            ):

                print(
                    "Validated tracking match: "
                    f"{variant}"
                )

                return row

            print(
                "Rejected tracking candidate "
                "because returned row tracking "
                "does not match."
            )

        except Exception as e:

            print(
                f"Workbook tracking search "
                f"error for {variant}: {e}"
            )

    return None


def try_invoice_search(
    value
):
    """
    Search workbook by invoice number.

    Uses search_tracking because the existing
    workbook_reader already exposes that lookup.
    """

    value = clean_value(value)

    if not value:
        return None

    variants = []

    def add_variant(v):
        if not v:
            return

        if v not in variants:
            variants.append(v)

    add_variant(value)

    normalized = normalize_invoice_number(
        value
    )

    if normalized:
        add_variant(normalized)

    for variant in variants:

        try:

            print(
                f"Trying workbook invoice: "
                f"{variant}"
            )

            row = search_tracking(
                variant
            )

            if not row:
                continue

            if row_matches_invoice(
                row,
                value
            ):

                print(
                    "Validated invoice-number "
                    f"match: {variant}"
                )

                return row

            print(
                "Rejected invoice candidate "
                "because returned invoice "
                "number does not match."
            )

        except Exception as e:

            print(
                f"Invoice search error "
                f"for {variant}: {e}"
            )

    return None


def try_bol_search(
    value
):
    """
    Search workbook by BOL.

    BOL must be a real identifier.
    Generic POD/BOL text is rejected.
    """

    value = clean_value(value)

    normalized = normalize_bol(
        value
    )

    if not normalized:
        print(
            f"Rejected invalid BOL value: "
            f"{value}"
        )

        return None

    variants = [
        value,
        normalized,
    ]

    unique_variants = []

    for variant in variants:

        if (
            variant
            and variant not in unique_variants
        ):
            unique_variants.append(
                variant
            )

    for variant in unique_variants:

        try:

            print(
                f"Trying workbook BOL: "
                f"{variant}"
            )

            row = search_tracking(
                variant
            )

            if not row:
                continue

            if row_matches_bol(
                row,
                value
            ):

                print(
                    "Validated BOL match: "
                    f"{variant}"
                )

                return row

            print(
                "Rejected BOL candidate "
                "because returned row BOL "
                "does not match."
            )

        except Exception as e:

            print(
                f"BOL search error "
                f"for {variant}: {e}"
            )

    return None


# ============================================================
# SPLIT PO
# ============================================================

def extract_base_po(value):
    """
    Convert split-order PO into base PO.

    Examples:

        3121061A -> 3121061
        3121061B -> 3121061
        N170755A -> N170755

    Important:
        A trailing letter is removed only when
        the preceding portion contains digits.
    """

    value = clean_value(value)

    if not value:
        return None

    normalized = normalize_identifier(
        value
    )

    if not normalized:
        return None

    if len(normalized) <= 1:
        return None

    last_character = normalized[-1]

    if last_character.isalpha():

        base = normalized[:-1]

        if (
            base
            and any(
                character.isdigit()
                for character in base
            )
        ):

            return base

    return None


# ============================================================
# WORKBOOK SEARCH
# ============================================================

def search_workbook_for_pdf_data(
    pdf_data,
    invoice_type
):
    """
    Search workbook using identifiers extracted
    from the PDF.

    Search priority:

        1. Exact PO
        2. Split/base PO
        3. Tracking
        4. Invoice number
        5. BOL

    Every returned candidate is validated.
    """

    # ========================================================
    # 1. PO
    # ========================================================

    pdf_po = clean_po(
        pdf_data.get("po")
    )

    if pdf_po:

        print()
        print(
            f"Trying PDF PO: {pdf_po}"
        )

        row = try_workbook_search(
            pdf_po
        )

        if row:
            return row, "PDF PO"

        # Explicit base PO search.
        base_po = extract_base_po(
            pdf_po
        )

        if base_po:

            print(
                f"Trying base/split PO: "
                f"{base_po}"
            )

            row = try_workbook_search(
                base_po
            )

            if row:
                return row, "Base PO"

    # ========================================================
    # 2. TRACKING
    # ========================================================

    tracking = clean_value(
        pdf_data.get("tracking")
    )

    if tracking:

        print()
        print(
            f"Trying tracking number: "
            f"{tracking}"
        )

        row = try_tracking_search(
            tracking
        )

        if row:
            return row, "Tracking"

    # ========================================================
    # 3. INVOICE NUMBER
    # ========================================================

    invoice_number = clean_value(
        pdf_data.get("invoice_number")
    )

    if invoice_number:

        print()
        print(
            f"Trying invoice number: "
            f"{invoice_number}"
        )

        row = try_invoice_search(
            invoice_number
        )

        if row:
            return row, "Invoice Number"

        # Some existing workbooks may store
        # invoice as a PO-like field.
        row = try_workbook_search(
            invoice_number
        )

        if row:

            workbook_po = normalize_po(
                get_row_po(row)
            )

            invoice_normalized = (
                normalize_invoice_number(
                    invoice_number
                )
            )

            if (
                workbook_po
                == invoice_normalized
            ):

                return (
                    row,
                    "Invoice Number"
                )

    # ========================================================
    # 4. BOL
    # ========================================================

    bol = clean_value(
        pdf_data.get("bol")
    )

    if bol:

        print()
        print(
            f"Trying BOL: {bol}"
        )

        row = try_bol_search(
            bol
        )

        if row:
            return row, "BOL"

    return None, None


# ============================================================
# AMOUNT CONVERSION
# ============================================================

def amount_to_float(value):
    """
    Convert currency/numeric values safely to float.
    """

    if value is None:
        return None

    try:

        if isinstance(value, float):

            if math.isnan(value):
                return None

            if math.isinf(value):
                return None

    except Exception:
        pass

    try:

        text = str(value).strip()

        if text.lower() in {
            "",
            "nan",
            "none",
            "null",
            "na",
            "n/a",
        }:
            return None

        text = (
            text
            .replace(",", "")
            .replace("$", "")
            .strip()
        )

        if not text:
            return None

        amount = float(text)

        if math.isnan(amount):
            return None

        if math.isinf(amount):
            return None

        return amount

    except Exception:
        return None


# ============================================================
# PRICE COMPARISON
# ============================================================

def compare_prices(
    pdf_price,
    workbook_row,
    invoice_type=None
):
    """
    Carrier-specific price comparison.

    FEDEX / UPS / RL / PRIORITY1:
        PDF amount must match Workbook Freight.

    NASSAU:
        PDF sales invoice is compared against:
            Gross
            Extended
            Net
            Extended + Freight
            Extended + Tax
            Extended + Freight + Tax

    Returns:

        (True, reason)
        (False, reason)
        (None, reason)
    """

    pdf_amount = amount_to_float(
        pdf_price
    )

    if pdf_amount is None:

        return (
            None,
            f"PDF price is invalid: "
            f"{pdf_price}"
        )

    gross = amount_to_float(
        get_workbook_value(
            workbook_row,
            "Gross"
        )
    )

    extended = amount_to_float(
        get_workbook_value(
            workbook_row,
            "Extended"
        )
    )

    freight = amount_to_float(
        get_workbook_value(
            workbook_row,
            "Freight"
        )
    )

    net = amount_to_float(
        get_workbook_value(
            workbook_row,
            "Net"
        )
    )

    tax = amount_to_float(
        get_workbook_value(
            workbook_row,
            "Tax"
        )
    )

    miscellaneous = amount_to_float(
        get_workbook_value(
            workbook_row,
            "Miscellaneous"
        )
    )

    discount = amount_to_float(
        get_workbook_value(
            workbook_row,
            "Discount"
        )
    )

    print()
    print(
        f"PDF amount       : ${pdf_amount:.2f}"
    )

    print(
        f"Workbook Gross   : {gross}"
    )

    print(
        f"Workbook Extended: {extended}"
    )

    print(
        f"Workbook Freight : {freight}"
    )

    print(
        f"Workbook Net     : {net}"
    )

    print(
        f"Workbook Tax     : {tax}"
    )

    # ========================================================
    # CARRIER INVOICES
    # ========================================================

    carrier_invoice_types = {
        "FEDEX",
        "UPS",
        "RL",
        "PRIORITY1",
    }

    if invoice_type in carrier_invoice_types:

        if freight is None:

            reason = (
                "Carrier invoice price "
                f"${pdf_amount:.2f} cannot be "
                "verified because Workbook "
                "Freight is unavailable."
            )

            print(
                f"❌ {reason}"
            )

            return False, reason

        difference = abs(
            pdf_amount
            - freight
        )

        print()
        print(
            "Carrier freight comparison:"
        )

        print(
            f"PDF carrier charge : "
            f"${pdf_amount:.2f}"
        )

        print(
            f"Workbook Freight   : "
            f"${freight:.2f}"
        )

        print(
            f"Difference         : "
            f"${difference:.2f}"
        )

        if difference <= 0.01:

            reason = (
                "Carrier invoice price "
                f"${pdf_amount:.2f} matches "
                f"Workbook Freight "
                f"${freight:.2f}."
            )

            print(
                f"✅ {reason}"
            )

            return True, reason

        reason = (
            "Carrier invoice price "
            f"${pdf_amount:.2f} does not "
            f"match Workbook Freight "
            f"${freight:.2f}; difference "
            f"${difference:.2f}."
        )

        print(
            f"❌ {reason}"
        )

        return False, reason

    # ========================================================
    # NASSAU SALES INVOICE
    # ========================================================

    candidates = []

    if gross is not None:

        candidates.append(
            ("Gross", gross)
        )

    if extended is not None:

        candidates.append(
            ("Extended", extended)
        )

    if net is not None:

        candidates.append(
            ("Net", net)
        )

    # Direct comparisons.
    for label, amount in candidates:

        difference = abs(
            pdf_amount
            - amount
        )

        if difference <= 0.01:

            reason = (
                f"Nassau invoice price "
                f"${pdf_amount:.2f} matches "
                f"Workbook {label} "
                f"${amount:.2f}."
            )

            print(
                f"✅ {reason}"
            )

            return True, reason

    # Extended + Freight.
    if (
        extended is not None
        and freight is not None
    ):

        combined = (
            extended
            + freight
        )

        difference = abs(
            pdf_amount
            - combined
        )

        if difference <= 0.01:

            reason = (
                f"Nassau invoice price "
                f"${pdf_amount:.2f} matches "
                f"Workbook Extended + Freight "
                f"${combined:.2f}."
            )

            print(
                f"✅ {reason}"
            )

            return True, reason

    # Extended + Tax.
    if (
        extended is not None
        and tax is not None
    ):

        combined = (
            extended
            + tax
        )

        difference = abs(
            pdf_amount
            - combined
        )

        if difference <= 0.01:

            reason = (
                f"Nassau invoice price "
                f"${pdf_amount:.2f} matches "
                f"Workbook Extended + Tax "
                f"${combined:.2f}."
            )

            print(
                f"✅ {reason}"
            )

            return True, reason

    # Extended + Freight + Tax.
    if (
        extended is not None
        and freight is not None
        and tax is not None
    ):

        combined = (
            extended
            + freight
            + tax
        )

        difference = abs(
            pdf_amount
            - combined
        )

        if difference <= 0.01:

            reason = (
                f"Nassau invoice price "
                f"${pdf_amount:.2f} matches "
                f"Workbook Extended + Freight "
                f"+ Tax ${combined:.2f}."
            )

            print(
                f"✅ {reason}"
            )

            return True, reason

    reason = (
        f"Nassau invoice price "
        f"${pdf_amount:.2f} does not match "
        f"available workbook amounts. "
        f"Gross={gross}, "
        f"Extended={extended}, "
        f"Freight={freight}, "
        f"Net={net}, "
        f"Tax={tax}, "
        f"Miscellaneous={miscellaneous}, "
        f"Discount={discount}."
    )

    print(
        f"❌ {reason}"
    )

    return False, reason


# ============================================================
# CSV ROW
# ============================================================

def make_csv_row(
    filename,
    invoice_type,
    pdf_data,
    workbook_row,
    matched_by,
    result,
    mismatch_reason=None
):
    """
    Build a CSV-safe row.
    """

    return {
        "File": filename,

        "Invoice Type": invoice_type,

        "Invoice Number": pdf_data.get(
            "invoice_number"
        ),

        "PDF PO": pdf_data.get(
            "po"
        ),

        "PDF Price": pdf_data.get(
            "price"
        ),

        "PDF Carrier": pdf_data.get(
            "carrier"
        ),

        "PDF Tracking": pdf_data.get(
            "tracking"
        ),

        "PDF BOL": pdf_data.get(
            "bol"
        ),

        "Customer": pdf_data.get(
            "customer"
        ),

        "Workbook PO": get_workbook_value(
            workbook_row,
            "PO"
        ),

        "Workbook Gross": get_workbook_value(
            workbook_row,
            "Gross"
        ),

        "Workbook Extended": get_workbook_value(
            workbook_row,
            "Extended"
        ),

        "Workbook Freight": get_workbook_value(
            workbook_row,
            "Freight"
        ),

        "Workbook Carrier": get_workbook_value(
            workbook_row,
            "Carrier"
        ),

        "Workbook Tracking": get_workbook_value(
            workbook_row,
            "Tracing Number",
            "Tracking Number",
            "Tracking",
            "PRO"
        ),

        "Matched By": matched_by,

        "Result": result,

        "Mismatch Reason": mismatch_reason or "",
    }


# ============================================================
# PROCESS INVOICES
# ============================================================

def process_invoices(
    queue_folder=DEFAULT_QUEUE_FOLDER,
    output_folder=DEFAULT_OUTPUT_FOLDER
):
    """
    Process all PDFs in queue and compare them
    against workbook data.
    """

    print()
    print("=" * 70)
    print(
        "JAN PROJECT - INVOICE PROCESSING"
    )
    print("=" * 70)

    os.makedirs(
        queue_folder,
        exist_ok=True
    )

    os.makedirs(
        output_folder,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Find PDFs
    # --------------------------------------------------------

    pdf_files = sorted(
        [
            os.path.join(
                queue_folder,
                filename
            )
            for filename in os.listdir(
                queue_folder
            )
            if filename.lower().endswith(
                ".pdf"
            )
        ]
    )

    print()
    print(
        f"Queue folder : {queue_folder}"
    )

    print(
        f"PDF files    : {len(pdf_files)}"
    )

    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    processed = 0
    matches = 0
    mismatches = 0
    po_not_found = 0
    skipped = 0

    skipped_files = []
    mismatch_rows = []

    # ========================================================
    # PROCESS EACH PDF
    # ========================================================

    for pdf_file in pdf_files:

        filename = os.path.basename(
            pdf_file
        )

        print()
        print("=" * 70)
        print(
            f"Processing PDF : {filename}"
        )
        print("=" * 70)

        # ----------------------------------------------------
        # DETECT TYPE
        # ----------------------------------------------------

        try:

            invoice_type = detect_invoice_type(
                pdf_file
            )

        except Exception as e:

            print(
                f"Detector error: {e}"
            )

            skipped += 1

            skipped_files.append(
                (
                    filename,
                    f"Detector error: {e}"
                )
            )

            continue

        print(
            f"Invoice Type   : {invoice_type}"
        )

        if (
            not invoice_type
            or invoice_type == "UNKNOWN"
        ):

            print(
                "Unsupported invoice type"
            )

            skipped += 1

            skipped_files.append(
                (
                    filename,
                    "Unsupported invoice type"
                )
            )

            continue

        # ----------------------------------------------------
        # GET READER
        # ----------------------------------------------------

        reader = get_reader(
            invoice_type
        )

        if reader is None:

            print(
                f"No reader configured for "
                f"{invoice_type}"
            )

            skipped += 1

            skipped_files.append(
                (
                    filename,
                    f"Reader unavailable: "
                    f"{invoice_type}"
                )
            )

            continue

        # ----------------------------------------------------
        # EXTRACT PDF DATA
        # ----------------------------------------------------

        try:

            pdf_data = reader(
                pdf_file
            )

        except Exception as e:

            print(
                f"PDF extraction error: {e}"
            )

            skipped += 1

            skipped_files.append(
                (
                    filename,
                    f"PDF extraction error: {e}"
                )
            )

            continue

        if not isinstance(
            pdf_data,
            dict
        ):

            print(
                "Reader returned invalid data"
            )

            skipped += 1

            skipped_files.append(
                (
                    filename,
                    "Invalid reader result"
                )
            )

            continue

        # ----------------------------------------------------
        # PRINT EXTRACTED DATA
        # ----------------------------------------------------

        print()
        print(
            "Extracted PDF Data"
        )

        print(
            "-" * 70
        )

        for key in [
            "invoice_number",
            "po",
            "price",
            "carrier",
            "tracking",
            "bol",
            "customer",
        ]:

            print(
                f"{key:<20}: "
                f"{pdf_data.get(key)}"
            )

        processed += 1

        # ----------------------------------------------------
        # SEARCH WORKBOOK
        # ----------------------------------------------------

        workbook_row, matched_by = (
            search_workbook_for_pdf_data(
                pdf_data,
                invoice_type
            )
        )

        if not workbook_row:

            print()
            print(
                "❌ PO / order not found "
                "in workbook"
            )

            po_not_found += 1

            skipped_files.append(
                (
                    filename,
                    "PO / order not found "
                    "in workbook"
                )
            )

            continue

        # ----------------------------------------------------
        # WORKBOOK MATCH FOUND
        # ----------------------------------------------------

        print()
        print(
            f"✅ Workbook match found "
            f"using: {matched_by}"
        )

        workbook_po = get_row_po(
            workbook_row
        )

        workbook_gross = get_workbook_value(
            workbook_row,
            "Gross"
        )

        workbook_extended = get_workbook_value(
            workbook_row,
            "Extended"
        )

        workbook_freight = get_workbook_value(
            workbook_row,
            "Freight"
        )

        workbook_carrier = get_workbook_value(
            workbook_row,
            "Carrier"
        )

        workbook_tracking = get_row_tracking(
            workbook_row
        )

        workbook_bol = get_row_bol(
            workbook_row
        )

        workbook_invoice = get_row_invoice(
            workbook_row
        )

        print()
        print(
            f"Workbook PO       : "
            f"{workbook_po}"
        )

        print(
            f"Workbook Gross    : "
            f"{workbook_gross}"
        )

        print(
            f"Workbook Extended : "
            f"{workbook_extended}"
        )

        print(
            f"Workbook Freight  : "
            f"{workbook_freight}"
        )

        print(
            f"Workbook Carrier  : "
            f"{workbook_carrier}"
        )

        print(
            f"Workbook Tracking : "
            f"{workbook_tracking}"
        )

        print(
            f"Workbook BOL      : "
            f"{workbook_bol}"
        )

        print(
            f"Workbook Invoice  : "
            f"{workbook_invoice}"
        )

        # ----------------------------------------------------
        # PRICE COMPARISON
        # ----------------------------------------------------

        price_result, price_reason = (
            compare_prices(
                pdf_data.get("price"),
                workbook_row,
                invoice_type
            )
        )

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        if price_result is True:

            matches += 1

            result = "MATCH"

            print()
            print(
                "✅ MATCH"
            )

        elif price_result is False:

            mismatches += 1

            result = "MISMATCH"

            print()
            print(
                "❌ MISMATCH"
            )

            print(
                f"Reason: {price_reason}"
            )

            mismatch_rows.append(
                make_csv_row(
                    filename,
                    invoice_type,
                    pdf_data,
                    workbook_row,
                    matched_by,
                    result,
                    price_reason
                )
            )

        else:

            mismatches += 1

            result = "UNABLE TO COMPARE"

            print()
            print(
                "⚠️ Unable to compare price"
            )

            print(
                f"Reason: {price_reason}"
            )

            mismatch_rows.append(
                make_csv_row(
                    filename,
                    invoice_type,
                    pdf_data,
                    workbook_row,
                    matched_by,
                    result,
                    price_reason
                )
            )

    # ========================================================
    # CREATE CSV REPORT
    # ========================================================

    report_path = os.path.join(
        output_folder,
        "mismatches.csv"
    )

    fieldnames = [
        "File",
        "Invoice Type",
        "Invoice Number",
        "PDF PO",
        "PDF Price",
        "PDF Carrier",
        "PDF Tracking",
        "PDF BOL",
        "Customer",
        "Workbook PO",
        "Workbook Gross",
        "Workbook Extended",
        "Workbook Freight",
        "Workbook Carrier",
        "Workbook Tracking",
        "Matched By",
        "Result",
        "Mismatch Reason",
    ]

    with open(
        report_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for row in mismatch_rows:

            writer.writerow(row)

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print(
        "CSV REPORT CREATED"
    )
    print("=" * 70)

    print(
        report_path
    )

    print()
    print("=" * 70)
    print(
        "SUMMARY"
    )
    print("=" * 70)

    print(
        f"Processed      : {processed}"
    )

    print(
        f"Matches        : {matches}"
    )

    print(
        f"Mismatches     : {mismatches}"
    )

    print(
        f"PO Not Found   : {po_not_found}"
    )

    print(
        f"Skipped        : {skipped}"
    )

    if skipped_files:

        print()
        print(
            "Skipped Files"
        )

        print(
            "-" * 70
        )

        for filename, reason in skipped_files:

            print(
                f"{filename} --> {reason}"
            )

    print()
    print(
        "CSV Report"
    )

    print(
        report_path
    )

    print()
    print("=" * 70)
    print(
        "PROCESSING COMPLETE"
    )
    print("=" * 70)

    return {
        "processed": processed,
        "matches": matches,
        "mismatches": mismatches,
        "po_not_found": po_not_found,
        "skipped": skipped,
        "report": report_path,
        "skipped_files": skipped_files,
    }