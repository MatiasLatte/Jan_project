import csv

CSV_FILE = "output/mismatches.csv"


def initialize_report():
    """
    Creates a fresh CSV file every time the program runs.
    """

    with open(CSV_FILE, "w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow([
            "PDF File",
            "Invoice Number",
            "PO",
            "PDF Amount",
            "Workbook Freight",
            "Difference",
            "Carrier",
            "Tracking",
            "Status"
        ])


def save_mismatch(pdf_data, workbook_data, pdf_filename):

    workbook_freight = float(workbook_data["Freight"])

    difference = round(
    pdf_data["price"] - workbook_freight,
    2
)

    with open(CSV_FILE, "a", newline="") as file:

        writer = csv.writer(file)

        writer.writerow([
            pdf_filename,
            pdf_data["invoice_number"],
            pdf_data["po"],
            pdf_data["price"],
            workbook_freight,
            difference,
            workbook_data["Carrier"],
            workbook_data.get("Tracing Number")
or workbook_data.get("Tracking Number", ""),
            "PRICE MISMATCH"
        ])


def save_po_not_found(pdf_data, pdf_filename):

    with open(CSV_FILE, "a", newline="") as file:

        writer = csv.writer(file)

        writer.writerow([
            pdf_filename,
            pdf_data["invoice_number"],
            pdf_data["po"],
            pdf_data["price"],
            "",
            "",
            pdf_data["carrier"],
            pdf_data["tracking"],
            "PO NOT FOUND"
        ])