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
QUEUE_FOLDER = "queue"
PROCESSED_FOLDER = "processed"
PROCESSED_LOG = "processed_pdfs.txt"

print("=" * 60)
print("Freight Invoice Validator")
print("=" * 60)

initialize_report()
# --------------------------------------------------
# Load processed PDFs
# --------------------------------------------------

processed_files = set()

if os.path.exists(PROCESSED_LOG):

    with open(PROCESSED_LOG, "r") as f:

        processed_files = {
            line.strip()
            for line in f
            if line.strip()
        }

processed = 0
matches = 0
mismatches = 0
missing_po = 0
skipped = 0

skipped_files = []

for filename in os.listdir(QUEUE_FOLDER):

    if not filename.lower().endswith(".pdf"):
        continue

    if filename in processed_files:

        print(f"Skipping already processed PDF : {filename}")

        continue

    pdf_file = os.path.join(QUEUE_FOLDER, filename)

    print("\n" + "=" * 70)
    print(f"Processing PDF : {filename}")
    print("=" * 70)

    try:

        print("Step 1 : Detecting invoice type...")

        invoice_type = detect_invoice_type(pdf_file)

        print(f"Detected Invoice Type : {invoice_type}")

        if invoice_type is None:

            print("❌ Could not determine invoice type")

            skipped += 1

            skipped_files.append(
        (filename, "Unknown invoice type")
    )
            
            continue

        print("Step 2 : Reading PDF...")

        if invoice_type == "PRIORITY1":
            pdf_data = priority1_reader(pdf_file)

        elif invoice_type == "RL":
            pdf_data = rl_reader(pdf_file)

        elif invoice_type == "FEDEX":
            pdf_data = fedex_reader(pdf_file)

        elif invoice_type == "UPS":
            pdf_data = ups_reader(pdf_file)

        else:

            print("❌ Unsupported invoice")

            skipped += 1

            skipped_files.append(
                (filename, "Unsupported invoice type")
            )

            continue

        processed += 1

        print("\nExtracted PDF Data")

        for key, value in pdf_data.items():
            print(f"{key:20}: {value}")

        if pdf_data["po"] is None:

            print("\n❌ PO Number could not be extracted")

            skipped += 1

            skipped_files.append(
                (filename, "PO Number not extracted")
            )

            continue
            print("=" * 60)
            print("PDF :", filename)
            print("PO  :", pdf_data["po"])
            print("Tracking :", pdf_data.get("tracking"))
            print("=" * 60)
        

        print("\nStep 3 : Searching Workbook...")

        workbook_data = None

# Try PO first
        if pdf_data["po"]:
         workbook_data = find_po(pdf_data["po"])

# If PO fails, try Tracking Number
        if workbook_data is None and pdf_data.get("tracking"):
            print("PO not found. Trying Tracking Number...")
        workbook_data = search_tracking(pdf_data["tracking"])
        

        if workbook_data is None:

            print(f"❌ PO {pdf_data['po']} NOT FOUND")

            save_po_not_found(
                pdf_data,
                filename
            )

            missing_po += 1

            continue

        print("Workbook record found.")

        print(f"Matched By : {workbook_data.get('Matched By', 'PO')}")

        print("\nWorkbook Values")

        for key, value in workbook_data.items():
            print(f"{key:20}: {value}")

        # --------------------------------------------------
        # Recipient Charge Validation (FedEx Only)
        # --------------------------------------------------

        if invoice_type == "FEDEX":

            print("\nRECIPIENT CHARGE VALIDATION")
            print("-" * 50)

            pdf_charge = float(pdf_data.get("recipient_charge") or 0)
            workbook_freight = float(workbook_data.get("Freight") or 0)

            print(f"PDF Recipient Charge : ${pdf_charge}")
            print(f"Workbook Freight     : ${workbook_freight}")

            charge_difference = abs(pdf_charge - workbook_freight)

            print(f"Difference           : ${charge_difference:.2f}")

            if charge_difference < 0.01:
                print("✅ RECIPIENT CHARGE MATCH")
            else:
                print("❌ RECIPIENT CHARGE MISMATCH")

        print("\nStep 4 : Comparing Prices...")

        result = compare(pdf_data, workbook_data)

        pdf_price = result["pdf_price"]

        workbook_price = result["workbook_freight"]

        difference = abs(pdf_price - workbook_price)

        print(f"PDF Price       : {pdf_price}")

        print(f"Workbook Price  : {workbook_price}")

        print(f"Difference      : {difference}")

        if difference < 0.01:

            print("✅ PRICE MATCH")

            matches += 1

            destination = os.path.join(PROCESSED_FOLDER, filename)

            shutil.move(pdf_file, destination)

            with open(PROCESSED_LOG, "a") as f:

                f.write(filename + "\n")

            print(f"Moved to processed folder : {filename}")

        else:

            print("❌ PRICE MISMATCH")

            mismatches += 1

            save_mismatch(
                pdf_data,
                workbook_data,
                filename
            )

            destination = os.path.join(PROCESSED_FOLDER, filename)

            shutil.move(pdf_file, destination)

            with open(PROCESSED_LOG, "a") as f:

                f.write(filename + "\n")

            print(f"Moved to processed folder : {filename}")

    except Exception as e:

        skipped += 1

        print("\n❌ ERROR PROCESSING PDF")

        print(e)

        traceback.print_exc()

        skipped_files.append(
            (filename, str(e))
        )

print("\n" + "=" * 70)

print("SUMMARY")

print("=" * 70)

print(f"Processed      : {processed}")

print(f"Matches        : {matches}")

print(f"Mismatches     : {mismatches}")

print(f"PO Not Found   : {missing_po}")

print(f"Skipped        : {skipped}")

print("\nSkipped Files")

print("-" * 70)

if len(skipped_files) == 0:

    print("None")

else:

    for file, reason in skipped_files:

        print(f"{file} --> {reason}")

print("\nCSV Report")

print("output/mismatches.csv")