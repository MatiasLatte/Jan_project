import os
import io

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


# ============================================================
# SETTINGS
# ============================================================

PROJECT_FOLDER = os.path.expanduser(
    "~/Documents/priority1_checker"
)

CREDENTIALS_FILE = os.path.join(
    PROJECT_FOLDER,
    "credentials.json"
)

TOKEN_FILE = os.path.join(
    PROJECT_FOLDER,
    "token.json"
)

# Google Drive structure
DRIVE_PROJECT_NAME = "JAN Project"
DRIVE_INPUT_FOLDER_NAME = "input"

# Local destination
LOCAL_INPUT_FOLDER = os.path.join(
    PROJECT_FOLDER,
    "input"
)

SCOPES = [
    "https://www.googleapis.com/auth/drive"
]


# ============================================================
# HELPER - ESCAPE GOOGLE DRIVE QUERY
# ============================================================

def escape_drive_query(value):

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

    credentials = None

    # --------------------------------------------------------
    # Load existing token
    # --------------------------------------------------------

    if os.path.exists(TOKEN_FILE):

        credentials = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    # --------------------------------------------------------
    # Refresh or authenticate
    # --------------------------------------------------------

    if not credentials or not credentials.valid:

        if (
            credentials
            and credentials.expired
            and credentials.refresh_token
        ):

            print(
                "Refreshing Google Drive authentication..."
            )

            credentials.refresh(
                Request()
            )

        else:

            print(
                "Opening Google authentication..."
            )

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES
            )

            credentials = flow.run_local_server(
                port=0
            )

        # Save token
        with open(
            TOKEN_FILE,
            "w"
        ) as token:

            token.write(
                credentials.to_json()
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

            status, done = downloader.next_chunk()

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
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("JAN PROJECT - GOOGLE DRIVE → LOCAL INPUT")
    print("=" * 60)
    print()

    # --------------------------------------------------------
    # Make sure local input folder exists
    # --------------------------------------------------------

    os.makedirs(
        LOCAL_INPUT_FOLDER,
        exist_ok=True
    )

    print(
        f"Local input folder:\n"
        f"{LOCAL_INPUT_FOLDER}"
    )

    print()

    # --------------------------------------------------------
    # Connect
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

        print(
            "ERROR: JAN Project folder "
            "was not found in Google Drive."
        )

        return

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

        print(
            "ERROR: input folder was not found "
            "inside JAN Project."
        )

        return

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

        return

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
        # Skip if already downloaded
        # ----------------------------------------------------

        if os.path.exists(local_path):

            print(
                f"Already exists locally, "
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

    print()
    print(
        "Google Drive → "
        "JAN Project/input → "
        "local input/"
    )

    print()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()