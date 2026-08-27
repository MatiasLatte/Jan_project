# JAN Project - Freight Invoice Validator

## Overview

The JAN Project is a Python-based freight invoice validation pipeline.

The system:

1. Connects to Google Drive.
2. Finds PDF invoices in `JAN Project/input`.
3. Downloads the PDFs to the Lambda temporary workspace.
4. Detects the invoice/carrier type.
5. Extracts invoice information from the PDF.
6. Looks up the related Purchase Order (PO) in the Nassau Excel workbook.
7. Compares the freight amount from the invoice with the workbook.
8. Generates a CSV report for mismatches and missing POs.
9. Moves processed PDFs into the processed workspace.
10. Returns a processing summary from the AWS Lambda handler.

---

## Python Version

The Lambda implementation is designed for:

**Python 3.13**

Local development was tested using Python 3.12.

---

## Project Structure

```text
lambda/
├── lambda_function.py
├── processor.py
├── download_from_drive.py
├── detector.py
├── priority1_reader.py
├── rl_reader.py
├── fedex_reader.py
├── ups_reader.py
├── workbook_reader.py
├── comparator.py
├── report_generator.py
├── Nassau.xlsx
├── requirements.txt
└── service_account.json        # Not committed to Git