import os
import shutil
import traceback

from detector import detect_invoice_type

from priority1_reader import extract_pdf_data as priority1_reader
from rl_reader import extract_pdf_data as rl_reader
from fedex_reader import extract_pdf_data as fedex_reader
from ups_reader import extract_pdf_data as ups_reader

from workbook_reader import find_po, search_tracking
from comparator import compare

from report_generator import (
    initialize_report,
    save_mismatch,
    save_po_not_found,
)


# ============================================================
# SETTINGS
# ============================================================

QUEUE_FOLDER = "queue"
PROCESSED_FOLDER = "processed"
PROCESSED_LOG = "processed_pdfs.txt"


# ============================================================
# PREPARE FOLDERS
# ============================================================

os.makedirs(QUEUE_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)


# ============================================================
# START
# ============================================================

print("=" * 60)
print("Freight Invoice Validator")
print("=" * 60)


# ============================================================
# INITIALIZE REPORT
# ============================================================

initialize_report()


# ============================================================
# LOAD PROCESSED PDFs
# ============================================================

processed_files = set()

if os.path.exists(PROCESSED_LOG):

    with open(PROCESSED_LOG, "r") as f:

        processed_files = {
            line.strip()
            for line in f
            if line.strip()
        }


# ============================================================
# CREATE A FIXED LIST OF QUEUE FILES
# ============================================================
#
# IMPORTANT:
# We create the list BEFORE processing.
#
# main.py moves processed PDFs from queue/ → processed/.
# Iterating directly over os.listdir(queue) while changing
# that directory can cause FileNotFoundError.
#
# ============================================================

queue_files = [
    filename
    for filename in os.listdir(QUEUE_FOLDER)
    if filename.lower().endswith(".pdf")
]


if not queue_files:

    print()
    print("No PDF files found in queue.")
    print()

    exit()


print()
print(f"Found {len(queue_files)} PDF(s) in queue.")
print()


# ============================================================
# COUNTERS
# ============================================================

processed = 0
matches = 0
mismatches = 0
missing_po = 0
skipped = 0

skipped_files = []


# ============================================================
# PROCESS PDFs
# ============================================================

for filename in queue_files:

    # --------------------------------------------------------
    # Skip already processed PDFs
    # --------------------------------------------------------

    if filename in processed_files:

        print(
            f"Skipping already processed PDF : {filename}"
        )

        continue


    pdf_file = os.path.join(
        QUEUE_FOLDER,
        filename
    )


    # --------------------------------------------------------
    # Make sure the file still exists
    # --------------------------------------------------------

    if not os.path.exists(pdf_file):

        print(
            f"Skipping missing PDF : {filename}"
        )

        skipped += 1

        skipped_files.append(
            (
                filename,
                "PDF no longer exists in queue"
            )
        )

        continue


    print("\n" + "=" * 70)
    print(f"Processing PDF : {filename}")
    print("=" * 70)


    try:

        # ====================================================
        # STEP 1 - DETECT INVOICE TYPE
        # ====================================================

        print("Step 1 : Detecting invoice type...")

        invoice_type = detect_invoice_type(
            pdf_file
        )

        print(
            f"Detected Invoice Type : {invoice_type}"
        )


        if invoice_type is None:

            print(
                "❌ Could not determine invoice type"
            )

            skipped += 1

            skipped_files.append(
                (
                    filename,
                    "Unknown invoice type"
                )
            )

            continue


        # ====================================================
        # STEP 2 - READ PDF
        # ====================================================

        print("Step 2 : Reading PDF...")


        if invoice_type == "PRIORITY1":

            pdf_data = priority1_reader(
                pdf_file
            )


        elif invoice_type == "RL":

            pdf_data = rl_reader(
                pdf_file
            )


        elif invoice_type == "FEDEX":

            pdf_data = fedex_reader(
                pdf_file
            )


        elif invoice_type == "UPS":

            pdf_data = ups_reader(
                pdf_file
            )


        else:

            print(
                "❌ Unsupported invoice"
            )

            skipped += 1

            skipped_files.append(
                (
                    filename,
                    "Unsupported invoice type"
                )
            )

            continue


        processed += 1


        # ====================================================
        # DISPLAY EXTRACTED DATA
        # ====================================================

        print()
        print("Extracted PDF Data")

        for key, value in pdf_data.items():

            print(
                f"{key:20}: {value}"
            )


        # ====================================================
        # CHECK PO
        # ====================================================

        if pdf_data.get("po") is None:

            print()
            print(
                "❌ PO Number could not be extracted"
            )

            skipped += 1

            skipped_files.append(
                (
                    filename,
                    "PO Number not extracted"
                )
            )

            continue


        print()
        print("=" * 60)
        print(f"PDF       : {filename}")
        print(f"PO        : {pdf_data.get('po')}")
        print(
            f"Tracking  : {pdf_data.get('tracking')}"
        )
        print("=" * 60)


        # ====================================================
        # STEP 3 - SEARCH WORKBOOK
        # ====================================================

        print()
        print(
            "Step 3 : Searching Workbook..."
        )


        workbook_data = None


        # ----------------------------------------------------
        # Try PO first
        # ----------------------------------------------------

        if pdf_data.get("po"):

            workbook_data = find_po(
                pdf_data["po"]
            )


        # ----------------------------------------------------
        # If PO not found, try Tracking Number
        # ----------------------------------------------------

        if (
            workbook_data is None
            and pdf_data.get("tracking")
        ):

            print(
                "PO not found. Trying Tracking Number..."
            )

            workbook_data = search_tracking(
                pdf_data["tracking"]
            )


        # ----------------------------------------------------
        # Workbook record not found
        # ----------------------------------------------------

        if workbook_data is None:

            print(
                f"❌ PO {pdf_data.get('po')} NOT FOUND"
            )

            save_po_not_found(
                pdf_data,
                filename
            )

            missing_po += 1

            continue


        print(
            "Workbook record found."
        )

        print(
            f"Matched By : "
            f"{workbook_data.get('Matched By', 'PO')}"
        )


        # ====================================================
        # DISPLAY WORKBOOK VALUES
        # ====================================================

        print()
        print("Workbook Values")

        for key, value in workbook_data.items():

            print(
                f"{key:20}: {value}"
            )


        # ====================================================
        # RECIPIENT CHARGE VALIDATION
        # FEDEX ONLY
        # ====================================================

        if invoice_type == "FEDEX":

            print()
            print(
                "RECIPIENT CHARGE VALIDATION"
            )

            print(
                "-" * 50
            )


            try:

                pdf_charge = float(
                    pdf_data.get(
                        "recipient_charge"
                    ) or 0
                )

            except (TypeError, ValueError):

                pdf_charge = 0


            try:

                workbook_freight = float(
                    workbook_data.get(
                        "Freight"
                    ) or 0
                )

            except (TypeError, ValueError):

                workbook_freight = 0


            print(
                f"PDF Recipient Charge : "
                f"${pdf_charge}"
            )

            print(
                f"Workbook Freight     : "
                f"${workbook_freight}"
            )


            charge_difference = abs(
                pdf_charge - workbook_freight
            )


            print(
                f"Difference           : "
                f"${charge_difference:.2f}"
            )


            if charge_difference < 0.01:

                print(
                    "✅ RECIPIENT CHARGE MATCH"
                )

            else:

                print(
                    "❌ RECIPIENT CHARGE MISMATCH"
                )


        # ====================================================
        # STEP 4 - COMPARE PRICES
        # ====================================================

        print()
        print(
            "Step 4 : Comparing Prices..."
        )


        result = compare(
            pdf_data,
            workbook_data
        )


        pdf_price = result[
            "pdf_price"
        ]

        workbook_price = result[
            "workbook_freight"
        ]


        difference = abs(
            pdf_price - workbook_price
        )


        print(
            f"PDF Price       : {pdf_price}"
        )

        print(
            f"Workbook Price  : {workbook_price}"
        )

        print(
            f"Difference      : {difference}"
        )


        # ====================================================
        # PRICE MATCH
        # ====================================================

        if difference < 0.01:

            print(
                "✅ PRICE MATCH"
            )

            matches += 1


            destination = os.path.join(
                PROCESSED_FOLDER,
                filename
            )


            # ------------------------------------------------
            # Make sure destination doesn't already exist
            # ------------------------------------------------

            if os.path.exists(destination):

                os.remove(destination)


            shutil.move(
                pdf_file,
                destination
            )


            # ------------------------------------------------
            # Record as processed
            # ------------------------------------------------

            with open(
                PROCESSED_LOG,
                "a"
            ) as f:

                f.write(
                    filename + "\n"
                )


            print(
                f"Moved to processed folder : "
                f"{filename}"
            )


        # ====================================================
        # PRICE MISMATCH
        # ====================================================

        else:

            print(
                "❌ PRICE MISMATCH"
            )

            mismatches += 1


            save_mismatch(
                pdf_data,
                workbook_data,
                filename
            )


            destination = os.path.join(
                PROCESSED_FOLDER,
                filename
            )


            if os.path.exists(destination):

                os.remove(destination)


            shutil.move(
                pdf_file,
                destination
            )


            # ------------------------------------------------
            # Record as processed
            # ------------------------------------------------

            with open(
                PROCESSED_LOG,
                "a"
            ) as f:

                f.write(
                    filename + "\n"
                )


            print(
                f"Moved to processed folder : "
                f"{filename}"
            )


    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as e:

        skipped += 1

        print()
        print(
            "❌ ERROR PROCESSING PDF"
        )

        print(e)

        traceback.print_exc()


        skipped_files.append(
            (
                filename,
                str(e)
            )
        )


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("SUMMARY")
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
    f"PO Not Found   : {missing_po}"
)

print(
    f"Skipped        : {skipped}"
)


# ============================================================
# SKIPPED FILES
# ============================================================

print()
print("Skipped Files")
print("-" * 70)


if len(skipped_files) == 0:

    print("None")

else:

    for file, reason in skipped_files:

        print(
            f"{file} --> {reason}"
        )


# ============================================================
# CSV REPORT
# ============================================================

print()
print("CSV Report")
print(
    "output/mismatches.csv"
)

print()
print("=" * 70)
print("PROCESSING COMPLETE")
print("=" * 70)