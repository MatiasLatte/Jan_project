import os
import smtplib

from dotenv import load_dotenv

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# EMAIL SETTINGS
# ============================================================

EMAIL_FROM = os.environ.get(
    "EMAIL_FROM",
    "jan.abhi007@gmail.com"
)

EMAIL_TO = os.environ.get(
    "EMAIL_TO",
    "matiasl@nassaunationalcable.com"
)

GMAIL_SMTP_HOST = os.environ.get(
    "GMAIL_SMTP_HOST",
    "smtp.gmail.com"
)

GMAIL_SMTP_PORT = int(
    os.environ.get(
        "GMAIL_SMTP_PORT",
        "587"
    )
)

GMAIL_APP_PASSWORD = os.environ.get(
    "GMAIL_APP_PASSWORD"
)


# ============================================================
# SEND REPORT EMAIL
# ============================================================

def send_report_email(processing_result):

    if not GMAIL_APP_PASSWORD:
        raise ValueError(
            "GMAIL_APP_PASSWORD is not configured."
        )

    report_file = processing_result.get(
        "report"
    )

    if not report_file:
        raise ValueError(
            "Processing result does not contain a report path."
        )

    if not os.path.exists(report_file):
        raise FileNotFoundError(
            f"Report file not found: {report_file}"
        )

    processed = processing_result.get(
        "processed",
        0
    )

    matches = processing_result.get(
        "matches",
        0
    )

    mismatches = processing_result.get(
        "mismatches",
        0
    )

    po_not_found = processing_result.get(
        "po_not_found",
        0
    )

    skipped = processing_result.get(
        "skipped",
        0
    )


    # ========================================================
    # CREATE EMAIL
    # ========================================================

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
        MIMEText(
            body,
            "plain"
        )
    )


    # ========================================================
    # ATTACH CSV REPORT
    # ========================================================

    with open(
        report_file,
        "rb"
    ) as file:

        attachment = MIMEApplication(
            file.read(),
            _subtype="csv"
        )


    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename="mismatches.csv"
    )


    message.attach(
        attachment
    )


    # ========================================================
    # CONNECT TO GMAIL SMTP
    # ========================================================

    print()
    print("Connecting to Gmail SMTP...")

    with smtplib.SMTP(
        GMAIL_SMTP_HOST,
        GMAIL_SMTP_PORT
    ) as server:

        server.ehlo()

        server.starttls()

        server.ehlo()

        server.login(
            EMAIL_FROM,
            GMAIL_APP_PASSWORD
        )

        server.sendmail(
            EMAIL_FROM,
            [EMAIL_TO],
            message.as_string()
        )


    # ========================================================
    # SUCCESS
    # ========================================================

    print()
    print("=" * 60)
    print("EMAIL SENT SUCCESSFULLY")
    print("=" * 60)

    print(
        f"From      : {EMAIL_FROM}"
    )

    print(
        f"To        : {EMAIL_TO}"
    )

    print(
        f"Attachment: {report_file}"
    )

    print("=" * 60)


    return {
        "email_sent": True,
        "recipient": EMAIL_TO,
        "attachment": report_file
    }
