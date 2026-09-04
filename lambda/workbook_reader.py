import os
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FOLDER = os.path.join(BASE_DIR, "data")


# ============================================================
# WORKBOOK STORAGE
# ============================================================

WORKBOOK_DATA = {}


# ============================================================
# HELPERS
# ============================================================

def clean_value(value):
    if value is None:
        return None

    if pd.isna(value):
        return None

    value = str(value).strip()

    if not value or value.lower() in {"nan", "none", "null"}:
        return None

    return value


def clean_number(value):
    value = clean_value(value)

    if value is None:
        return None

    try:
        return float(
            value.replace(",", "")
                 .replace("$", "")
                 .strip()
        )
    except Exception:
        return None


def normalize(value):
    value = clean_value(value)

    if value is None:
        return ""

    return (
        value.upper()
        .replace(" ", "")
        .replace("-", "")
        .replace(".", "")
    )


# ============================================================
# LOAD STANDARD NASSAU WORKBOOK
# ============================================================

def load_standard_workbook(file_path):

    try:

        excel = pd.ExcelFile(file_path)

        for sheet in excel.sheet_names:

            try:

                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet,
                    header=1,
                    dtype=str
                )

                df = df.dropna(how="all")

                if "PO" not in df.columns:
                    continue

                df["PO"] = (
                    df["PO"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                )

                key = (file_path, sheet)

                WORKBOOK_DATA[key] = df

                print(f"  Loaded sheet: {sheet}")

            except Exception as e:

                print(
                    f"  Could not load sheet "
                    f"{sheet}: {e}"
                )

    except Exception as e:

        print(
            f"Could not open "
            f"{os.path.basename(file_path)}: {e}"
        )


# ============================================================
# LOAD INDIVIDUAL INVOICE / ORDER ACKNOWLEDGMENT
# ============================================================

def load_individual_invoice(file_path):

    try:

        df = pd.read_excel(
            file_path,
            sheet_name="Sales Invoice",
            header=None,
            dtype=str
        )

        invoice_number = None
        customer_po = None
        invoice_total = None

        # ----------------------------------------------------
        # Find invoice number
        # ----------------------------------------------------

        for i, row in df.iterrows():

            values = [
                clean_value(x)
                for x in row.tolist()
            ]

            values = [
                x for x in values
                if x is not None
            ]

            if not values:
                continue

            row_text = " | ".join(values).upper()

            if "INVOICE #" in row_text:

                for j, value in enumerate(values):

                    if "INVOICE #" in value.upper():

                        if j + 1 < len(values):

                            invoice_number = (
                                values[j + 1]
                            )

                        break
        # ----------------------------------------------------
        # Find CUSTOMER PO #
        # ----------------------------------------------------

        for i, row in df.iterrows():

            raw_values = row.tolist()

            # Look for the cell containing CUSTOMER PO #
            po_index = None

            for j, value in enumerate(raw_values):

                value = clean_value(value)

                if (
                    value
                    and "CUSTOMER PO #" in value.upper()
                ):
                    po_index = j
                    break

            if po_index is None:
                continue

            # The PO value is normally on the next row
            # in the same column.
            if i + 1 < len(df):

                next_value = clean_value(
                    df.iloc[i + 1, po_index]
                )

                if next_value:
                    customer_po = next_value

            break
        
                    # Find the position of CUSTOMER PO #
            po_index = None

            for j, value in enumerate(values):

                        if value and "CUSTOMER PO #" in value.upper():

                            po_index = j
                            break

                        if (
                        po_index is not None
                        and po_index < len(next_row)
                    ):

                         customer_po = (
                            next_row[po_index]
                        )

            break

        # ----------------------------------------------------
        # Find invoice total
        # ----------------------------------------------------

        for i, row in df.iterrows():

            values = [
                clean_value(x)
                for x in row.tolist()
            ]

            values = [
                x for x in values
                if x is not None
            ]

            if not values:
                continue

            row_text = " | ".join(values).upper()

            if "INVOICE TOTAL" in row_text:

                # Usually the last numeric value
                # in the following row.

                if i + 1 < len(df):

                    next_values = [
                        clean_value(x)
                        for x in df.iloc[i + 1].tolist()
                    ]

                    numbers = []

                    for value in next_values:

                        number = clean_number(value)

                        if number is not None:
                            numbers.append(number)

                    if numbers:

                        invoice_total = numbers[-1]

                break

        print(
            f"  Loaded Sales Invoice: "
            f"{os.path.basename(file_path)}"
        )

        print(
            f"    Invoice : {invoice_number}"
        )

        print(
            f"    PO      : {customer_po}"
        )

        print(
            f"    Price   : {invoice_total}"
        )

        key = (file_path, "Sales Invoice")

        WORKBOOK_DATA[key] = {
            "type": "individual_invoice",
            "Invoice": invoice_number,
            "PO": customer_po,
            "Gross": invoice_total,
            "Extended": invoice_total,
            "Freight": 0.0,
            "Carrier": "Nassau National Cable",
            "Tracking Number": None,
            "BOL": None,
            "Worksheet": "Sales Invoice",
            "Workbook": os.path.basename(file_path),
        }

    except Exception as e:

        print(
            f"Could not load "
            f"{os.path.basename(file_path)}: {e}"
        )


# ============================================================
# LOAD ALL EXCEL FILES
# ============================================================

print()
print("=" * 70)
print("LOADING WORKBOOK DATA")
print("=" * 70)

print(
    f"Data folder: {DATA_FOLDER}"
)


excel_files = sorted(
    [
        os.path.join(DATA_FOLDER, filename)
        for filename in os.listdir(DATA_FOLDER)
        if filename.lower().endswith(
            (".xlsx", ".xls", ".xlsm")
        )
        and not filename.startswith("~$")
    ]
)

print(
    f"Excel files found: {len(excel_files)}"
)


for file_path in excel_files:

    filename = os.path.basename(file_path)

    print()
    print(
        f"Loading workbook: {filename}"
    )

    if filename.lower() == "nassau.xlsx":

        load_standard_workbook(file_path)

    else:

        load_individual_invoice(file_path)


print()
print("=" * 70)
print(
    f"Total worksheets loaded: "
    f"{len(WORKBOOK_DATA)}"
)
print("=" * 70)


# ============================================================
# FIND PO
# ============================================================

def find_po(po_number):

    po_number = clean_value(po_number)

    if not po_number:
        return None

    target = normalize(po_number)

    # --------------------------------------------------------
    # Search individual invoice workbooks
    # --------------------------------------------------------

    for key, data in WORKBOOK_DATA.items():

        if not isinstance(data, dict):
            continue

        workbook_po = data.get("PO")

        if normalize(workbook_po) == target:

            row = dict(data)

            row["Matched By"] = "PO"

            print(
                f"Found PO {po_number} "
                f"in workbook "
                f"{row.get('Workbook')}"
            )

            return row

    # --------------------------------------------------------
    # Search normal workbook sheets
    # --------------------------------------------------------

    for key, df in WORKBOOK_DATA.items():

        if not isinstance(df, pd.DataFrame):
            continue

        if "PO" not in df.columns:
            continue

        values = (
            df["PO"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        match = df[
            values == str(po_number).strip().upper()
        ]

        if not match.empty:

            row = match.iloc[0].to_dict()

            row["Worksheet"] = key[1]

            row["Workbook"] = os.path.basename(
                key[0]
            )

            row["Matched By"] = "PO"

            freight = clean_number(
                row.get("Freight")
            )

            row["Freight"] = (
                freight
                if freight is not None
                else 0.0
            )

            return row

    # --------------------------------------------------------
    # Search Split Order PO
    # --------------------------------------------------------

    for key, df in WORKBOOK_DATA.items():

        if not isinstance(df, pd.DataFrame):
            continue

        if "Split Order PO#" not in df.columns:
            continue

        values = (
            df["Split Order PO#"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        match = df[
            values == str(po_number).strip().upper()
        ]

        if not match.empty:

            row = match.iloc[0].to_dict()

            row["Worksheet"] = key[1]

            row["Workbook"] = os.path.basename(
                key[0]
            )

            row["Matched By"] = (
                "Split Order PO"
            )

            freight = clean_number(
                row.get("Freight")
            )

            row["Freight"] = (
                freight
                if freight is not None
                else 0.0
            )

            print(
                f"Found using Split Order PO "
                f"in {key[1]}"
            )

            return row

    return None


# ============================================================
# SEARCH TRACKING / INVOICE / BOL
# ============================================================

def search_tracking(tracking):

    tracking = clean_value(tracking)

    if not tracking:
        return None

    target = normalize(tracking)

    # --------------------------------------------------------
    # Individual invoice workbooks
    # --------------------------------------------------------

    for key, data in WORKBOOK_DATA.items():

        if not isinstance(data, dict):
            continue

        fields = [
            "Tracking Number",
            "Tracking",
            "PRO",
            "BOL",
            "Invoice",
        ]

        for field in fields:

            value = data.get(field)

            if normalize(value) == target:

                row = dict(data)

                row["Matched By"] = field

                print(
                    f"FOUND {tracking} "
                    f"in {row.get('Workbook')}"
                )

                return row

    # --------------------------------------------------------
    # Standard workbook sheets
    # --------------------------------------------------------

    for key, df in WORKBOOK_DATA.items():

        if not isinstance(df, pd.DataFrame):
            continue

        for col in df.columns:

            values = (
                df[col]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            normalized_values = (
                values
                .str.upper()
            )

            if target in {
                normalize(x)
                for x in values
            }:

                match = df[
                    normalized_values
                    == str(tracking).strip().upper()
                ]

                if not match.empty:

                    row = (
                        match.iloc[0]
                        .to_dict()
                    )

                    row["Worksheet"] = key[1]

                    row["Workbook"] = (
                        os.path.basename(key[0])
                    )

                    row["Matched By"] = col

                    print()
                    print(
                        f"FOUND in sheet: "
                        f"{key[1]}"
                    )

                    print(
                        f"Column: {col}"
                    )

                    return row

    print(
        f"Tracking / identifier "
        f"not found: {tracking}"
    )

    return None