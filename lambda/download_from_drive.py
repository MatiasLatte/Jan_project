import os
import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


# ============================================================
# SETTINGS
# ============================================================

# Lambda temporary workspace
LAMBDA_TMP = os.environ.get(
    "LAMBDA_TMP",
    "/tmp/jan_project"
)

# Service account credentials
SERVICE_ACCOUNT_FILE = os.path.join(
    os.path.dirname(__file__),
    "service_account.json"
)

# Google Drive structure
DRIVE_PROJECT_NAME = os.environ.get(
    "GOOGLE_DRIVE_PROJECT_FOLDER",
    "JAN Project"
)

DRIVE_INPUT_FOLDER_NAME = os.environ.get(
    "GOOGLE_DRIVE_INPUT_FOLDER",
    "input"
)

# Local Lambda destination
LOCAL_INPUT_FOLDER = os.path.join(
    LAMBDA_TMP,
    "queue"
)

SCOPES = [
    "https://www.googleapis.com/auth/drive"
]


# ============================================================
# HELPER - ESCAPE GOOGLE DRIVE QUERY
# ============================================================

def escape_drive_query(value):
    """
    Safely escape a value used inside a Google Drive query.
    """
    return value.replace(
        "\\",
        "\\\\"
    ).replace(
        "'",
        "\\'"
    )


# ============================================================
# CONNECT TO GOOGLE DRIVE
# ============================================================

def connect_to_drive():
    """
    Connect to Google Drive using the Lambda service account.
    """

    credentials = (
        service_account.Credentials
        .from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )
    )

    drive = build(
        "drive",
        "v3",
        credentials=credentials
    )

    print(
        "Google Drive connected successfully!"
    )

    return drive


# ============================================================
# FIND DRIVE FOLDER
# ============================================================

def find_folder(
    drive,
    folder_name,
    parent_id=None
):
    """
    Find a Google Drive folder by name.
    """

    escaped_name = escape_drive_query(
        folder_name
    )

    query = (
        f"name = '{escaped_name}' "
        "and mimeType = "
        "'application/vnd.google-apps.folder' "
        "and trashed = false"
    )

    if parent_id:

        query += (
            f" and '{parent_id}' in parents"
        )

    results = drive.files().list(
        q=query,
        spaces="drive",
        fields="files(id,name)"
    ).execute()

    folders = results.get(
        "files",
        []
    )

    if not folders:

        return None

    return folders[0]["id"]


# ============================================================
# FIND PDF FILES
# ============================================================

def find_pdfs(
    drive,
    folder_id
):
    """
    Find all PDF files inside a Drive folder.
    """

    query = (
        f"'{folder_id}' in parents "
        "and mimeType = 'application/pdf' "
        "and trashed = false"
    )

    files = []

    page_token = None

    while True:

        results = drive.files().list(
            q=query,
            spaces="drive",
            fields="nextPageToken,files(id,name,size)",
            pageToken=page_token
        ).execute()

        files.extend(
            results.get(
                "files",
                []
            )
        )

        page_token = results.get(
            "nextPageToken"
        )

        if not page_token:

            break

    return files


# ============================================================
# DOWNLOAD PDF
# ============================================================

def download_pdf(
    drive,
    file_id,
    file_name,
    destination
):
    """
    Download one PDF from Google Drive
    into the Lambda temporary directory.
    """

    request = drive.files().get_media(
        fileId=file_id
    )

    with open(
        destination,
        "wb"
    ) as local_file:

        downloader = MediaIoBaseDownload(
            local_file,
            request
        )

        done = False

        while not done:

            status, done = (
                downloader.next_chunk()
            )

            if status:

                progress = int(
                    status.progress() * 100
                )

                print(
                    f"Downloading {file_name}: "
                    f"{progress}%"
                )

    print(
        f"Downloaded successfully: {file_name}"
    )


# ============================================================
# DOWNLOAD DRIVE INPUT
# ============================================================

def download_drive_input():
    """
    Download PDFs from:

        Google Drive
            JAN Project
                input/

    into:

        /tmp/jan_project/queue/
    """

    print()
    print("=" * 60)
    print("JAN PROJECT - GOOGLE DRIVE → LAMBDA")
    print("=" * 60)
    print()

    # --------------------------------------------------------
    # Prepare Lambda temporary folder
    # --------------------------------------------------------

    os.makedirs(
        LOCAL_INPUT_FOLDER,
        exist_ok=True
    )

    print(
        f"Lambda input folder:\n"
        f"{LOCAL_INPUT_FOLDER}"
    )

    print()

    # --------------------------------------------------------
    # Connect to Google Drive
    # --------------------------------------------------------

    drive = connect_to_drive()

    print()

    # --------------------------------------------------------
    # Find JAN Project
    # --------------------------------------------------------

    project_folder_id = find_folder(
        drive,
        DRIVE_PROJECT_NAME
    )

    if not project_folder_id:

        raise RuntimeError(
            "JAN Project folder was not found "
            "in Google Drive."
        )

    print(
        f"Found Drive folder: "
        f"{DRIVE_PROJECT_NAME}"
    )

    # --------------------------------------------------------
    # Find input folder
    # --------------------------------------------------------

    input_folder_id = find_folder(
        drive,
        DRIVE_INPUT_FOLDER_NAME,
        project_folder_id
    )

    if not input_folder_id:

        raise RuntimeError(
            "input folder was not found "
            "inside JAN Project."
        )

    print(
        "Found Drive folder: "
        "JAN Project/input"
    )

    print()

    # --------------------------------------------------------
    # Find PDFs
    # --------------------------------------------------------

    pdf_files = find_pdfs(
        drive,
        input_folder_id
    )

    print(
        f"Found {len(pdf_files)} PDF(s) "
        "in Google Drive input."
    )

    if not pdf_files:

        print(
            "No PDFs to download."
        )

        return {
            "downloaded": 0,
            "skipped": 0,
            "total": 0
        }

    print()

    # --------------------------------------------------------
    # Download PDFs
    # --------------------------------------------------------

    downloaded = 0
    skipped = 0

    for pdf in pdf_files:

        file_name = pdf["name"]

        local_path = os.path.join(
            LOCAL_INPUT_FOLDER,
            file_name
        )

        # ----------------------------------------------------
        # Skip existing files
        # ----------------------------------------------------

        if os.path.exists(local_path):

            print(
                f"Already exists in Lambda, "
                f"skipping: {file_name}"
            )

            skipped += 1

            continue

        # ----------------------------------------------------
        # Download
        # ----------------------------------------------------

        try:

            download_pdf(
                drive,
                pdf["id"],
                file_name,
                local_path
            )

            downloaded += 1

        except Exception as error:

            print(
                f"ERROR downloading "
                f"{file_name}: {error}"
            )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("DOWNLOAD COMPLETE")
    print("=" * 60)

    print(
        f"Downloaded : {downloaded}"
    )

    print(
        f"Skipped    : {skipped}"
    )

    print(
        f"Total      : {len(pdf_files)}"
    )

    print()

    return {
        "downloaded": downloaded,
        "skipped": skipped,
        "total": len(pdf_files)
    }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    download_drive_input()