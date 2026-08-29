import os
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


AWS_SES_REGION = os.environ.get(
    "AWS_SES_REGION",
    "ap-southeast-2"
)

EMAIL_FROM = os.environ.get(
    "EMAIL_FROM",
    "jan.abhi007@gmail.com"
)

EMAIL_TO = os.environ.get(
    "EMAIL_TO",
    "matiasl@nassaunationalcable.com"
)


def send_report_email(processing_result):

    report_file = processing_result.get("report")

    if not report_file:
        raise ValueError(
            "Processing result does not contain a report path."
        )

    if not os.path.exists(report_file):
        raise FileNotFoundError(
            f"Report file not found: {report_file}"
        )

    processed = processing_result.get("processed", 0)
    matches = processing_result.get("matches", 0)
    mismatches = processing_result.get("mismatches", 0)
    po_not_found = processing_result.get("po_not_found", 0)
    skipped = processing_result.get("skipped", 0)

    message = MIMEMultipart()

    message["Subject"] = (
        "JAN Project - Freight Invoice Validation Report"
    )

    message["From"] = EMAIL_FROM
    message["To"] = EMAIL_TO

    body = f"""JAN Project Freight Invoice Validation

Processing Summary
------------------
Processed    : {processed}
Matches      : {matches}
Mismatches   : {mismatches}
PO Not Found : {po_not_found}
Skipped      : {skipped}

The detailed CSV report is attached to this email.

JAN Project
Freight Invoice Validation Pipeline
"""

    message.attach(
        MIMEText(body, "plain")
    )

    with open(report_file, "rb") as file:
        attachment = MIMEApplication(
            file.read(),
            _subtype="csv"
        )

    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename="mismatches.csv"
    )

    message.attach(attachment)

    ses = boto3.client(
        "ses",
        region_name=AWS_SES_REGION
    )

    response = ses.send_raw_email(
        Source=EMAIL_FROM,
        Destinations=[EMAIL_TO],
        RawMessage={
            "Data": message.as_string()
        }
    )

    print("Report email sent successfully.")
    print(
        f"SES Message ID: {response['MessageId']}"
    )

    return {
        "email_sent": True,
        "message_id": response["MessageId"],
        "recipient": EMAIL_TO
    }
