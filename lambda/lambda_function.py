from download_from_drive import download_drive_input
from processor import process_invoices


def lambda_handler(event, context):

    print("=" * 60)
    print("JAN PROJECT LAMBDA")
    print("=" * 60)

    try:

        # ----------------------------------------------------
        # Step 1: Download PDFs from Google Drive
        # ----------------------------------------------------

        download_result = download_drive_input()

        # ----------------------------------------------------
        # Step 2: Process downloaded PDFs
        # ----------------------------------------------------

        processing_result = process_invoices()

        # ----------------------------------------------------
        # Final response
        # ----------------------------------------------------

        return {
            "statusCode": 200,
            "body": {
                "download": download_result,
                "processing": processing_result
            }
        }

    except Exception as error:

        print("Lambda processing failed:")
        print(error)

        return {
            "statusCode": 500,
            "body": {
                "error": str(error)
            }
        }


if __name__ == "__main__":

    result = lambda_handler({}, {})

    print()
    print("=" * 60)
    print("LAMBDA TEST RESULT")
    print("=" * 60)
    print(result)