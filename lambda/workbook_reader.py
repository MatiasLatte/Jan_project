import os
import pandas as pd

WORKBOOK = os.path.join(
    os.path.dirname(__file__),
    "Nassau.xlsx"
)

SHEETS = [
    "eBay, Amazon & Walmart",
    "NNC NES & Non-Wire",
    "Offline Orders",
    "Government Bidding",
    "Exports"
]

# -----------------------------
# Load workbook once
# -----------------------------

WORKBOOK_DATA = {}

for sheet in SHEETS:

    try:

        df = pd.read_excel(
            WORKBOOK,
            sheet_name=sheet,
            header=1,
            dtype=str
        )

        df = df.dropna(how="all")

        if "PO" not in df.columns:
            continue

        df["PO"] = (
            df["PO"]
            .astype(str)
            .str.strip()
        )

        WORKBOOK_DATA[sheet] = df

        print(f"Loaded sheet: {sheet}")

    except Exception as e:

        print(f"Could not load {sheet}: {e}")


def find_po(po_number):

    po_number = str(po_number).strip().upper()

    # --------------------------------------------------
    # First: Search normal PO column
    # --------------------------------------------------
    for sheet, df in WORKBOOK_DATA.items():

        match = df[df["PO"].astype(str).str.strip().str.upper() == po_number]

        if not match.empty:

            row = match.iloc[0].to_dict()
            row["Worksheet"] = sheet

            try:
                row["Freight"] = float(row["Freight"])
            except:
                row["Freight"] = 0.0

            row["Matched By"] = "PO"

            return row

    # --------------------------------------------------
    # Second: Search Split Order PO column
    # --------------------------------------------------
    for sheet, df in WORKBOOK_DATA.items():

        if "Split Order PO#" not in df.columns:
            continue

        split_col = (
            df["Split Order PO#"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        match = df[split_col == po_number]

        if not match.empty:

            print(f"Found using Split Order PO in {sheet}")

            row = match.iloc[0].to_dict()
            row["Worksheet"] = sheet

            try:
                row["Freight"] = float(row["Freight"])
            except:
                row["Freight"] = 0.0

            row["Matched By"] = "Split Order PO"

            return row

    return None

def search_tracking(tracking):

    tracking = str(tracking).strip()

    for sheet, df in WORKBOOK_DATA.items():

        for col in df.columns:

            values = (
                df[col]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            if tracking in values.values:

                print(f"\nFOUND in sheet: {sheet}")
                print(f"Column: {col}")

                row = df[values == tracking].iloc[0]
                print(row)

                return row.to_dict()

    print("NOT FOUND")