import json

from download_from_drive import download_drive_input
from processor import process_invoices
from email_sender import send_report_email


def lambda_handler(event, context):

    print("=" * 60)
    print("JAN PROJECT LAMBDA")
    print("=" * 60)

    try:

        # ----------------------------------------------------
        # Step 1: Download PDFs from Google Drive
        # ----------------------------------------------------

        print()
        print("STEP 1: Downloading PDFs from Google Drive...")

        download_result = download_drive_input()

        # ----------------------------------------------------
        # Step 2: Process downloaded PDFs
        # ----------------------------------------------------

        print()
        print("STEP 2: Processing invoices...")

        processing_result = process_invoices()

        # ----------------------------------------------------
        # Step 3: Send report by email
        # ----------------------------------------------------

        print()
        print("STEP 3: Sending report by email...")

        email_result = send_report_email(
            processing_result
        )

        # ----------------------------------------------------
        # Final response
        # ----------------------------------------------------

        response_body = {
            "status": "success",
            "download": download_result,
            "processing": processing_result,
            "email": email_result
        }

        print()
        print("=" * 60)
        print("JAN PROJECT LAMBDA COMPLETE")
        print("=" * 60)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(
                response_body,
                default=str
            )
        }

    except Exception as error:

        print()
        print("=" * 60)
        print("JAN PROJECT LAMBDA FAILED")
        print("=" * 60)
        print(error)

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "status": "error",
                "error": str(error)
            })
        }


if __name__ == "__main__":

    result = lambda_handler(
        {},
        {}
    )

    print()
    print("=" * 60)
    print("LAMBDA TEST RESULT")
    print("=" * 60)
    print(result)
