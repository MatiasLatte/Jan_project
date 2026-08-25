import os

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# ============================================================
# SETTINGS
# ============================================================

# This script is inside the priority_checker project
PROJECT_FOLDER = os.path.expanduser("~/Documents/priority1_checker")

CREDENTIALS_FILE = os.path.join(
    PROJECT_FOLDER,
    "credentials.json"
)

TOKEN_FILE = os.path.join(
    PROJECT_FOLDER,
    "token.json"
)

# Google Drive folder where the project will be stored
DRIVE_PROJECT_NAME = "JAN Project"

# These are the ONLY folders we want to upload
FOLDERS_TO_UPLOAD = [
    "input",
    "processed",
    "output"
]

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
    return value.replace("\\", "\\\\").replace("'", "\\'")


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
    # Refresh or create authentication
    # --------------------------------------------------------

    if not credentials or not credentials.valid:

        if credentials and credentials.expired and credentials.refresh_token:

            print("Refreshing Google Drive authentication...")

            credentials.refresh(Request())

        else:

            print("Opening Google authentication...")

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES
            )

            credentials = flow.run_local_server(
                port=0
            )

        # Save token
        with open(TOKEN_FILE, "w") as token:
            token.write(credentials.to_json())

    # --------------------------------------------------------
    # Build Drive service
    # --------------------------------------------------------

    drive = build(
        "drive",
        "v3",
        credentials=credentials
    )

    print("Google Drive connected successfully!")

    return drive


# ============================================================
# FIND OR CREATE DRIVE FOLDER
# ============================================================

def find_or_create_folder(
    drive,
    folder_name,
    parent_id=None
):

    escaped_name = escape_drive_query(folder_name)

    query = (
        f"name = '{escaped_name}' "
        "and mimeType = 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )

    # If a parent folder was supplied
    if parent_id:

        query += f" and '{parent_id}' in parents"

    results = drive.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)"
    ).execute()

    folders = results.get("files", [])

    # --------------------------------------------------------
    # Folder already exists
    # --------------------------------------------------------

    if folders:

        folder_id = folders[0]["id"]

        print(
            f"Found Drive folder: {folder_name}"
        )

        return folder_id

    # --------------------------------------------------------
    # Create folder
    # --------------------------------------------------------

    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }

    if parent_id:

        metadata["parents"] = [parent_id]

    folder = drive.files().create(
        body=metadata,
        fields="id, name"
    ).execute()

    print(
        f"Created Drive folder: {folder_name}"
    )

    return folder["id"]


# ============================================================
# CHECK WHETHER FILE ALREADY EXISTS
# ============================================================

def file_exists(
    drive,
    file_name,
    parent_id
):

    escaped_name = escape_drive_query(file_name)

    query = (
        f"name = '{escaped_name}' "
        f"and '{parent_id}' in parents "
        "and trashed = false"
    )

    results = drive.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)"
    ).execute()

    files = results.get("files", [])

    return len(files) > 0


# ============================================================
# UPLOAD SINGLE FILE
# ============================================================

def upload_file(
    drive,
    local_path,
    parent_id
):

    file_name = os.path.basename(local_path)

    # --------------------------------------------------------
    # Don't upload duplicate files
    # --------------------------------------------------------

    if file_exists(
        drive,
        file_name,
        parent_id
    ):

        print(
            f"Already exists, skipping: {file_name}"
        )

        return

    # --------------------------------------------------------
    # Determine MIME type
    # --------------------------------------------------------

    extension = os.path.splitext(
        file_name
    )[1].lower()

    mime_types = {

        ".pdf":
            "application/pdf",

        ".xlsx":
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

        ".xls":
            "application/vnd.ms-excel",

        ".csv":
            "text/csv",

        ".txt":
            "text/plain",

        ".json":
            "application/json",

        ".py":
            "text/x-python",

        ".docx":
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",

        ".jpg":
            "image/jpeg",

        ".jpeg":
            "image/jpeg",

        ".png":
            "image/png"
    }

    mime_type = mime_types.get(
        extension,
        "application/octet-stream"
    )

    # --------------------------------------------------------
    # File metadata
    # --------------------------------------------------------

    metadata = {
        "name": file_name,
        "parents": [parent_id]
    }

    # --------------------------------------------------------
    # Upload
    # --------------------------------------------------------

    media = MediaFileUpload(
        local_path,
        mimetype=mime_type
    )

    uploaded_file = drive.files().create(
        body=metadata,
        media_body=media,
        fields="id, name"
    ).execute()

    print(
        f"Uploaded: {uploaded_file['name']}"
    )


# ============================================================
# UPLOAD FOLDER CONTENTS
# ============================================================

def upload_folder(
    drive,
    local_folder,
    drive_folder_id
):

    print()
    print(
        f"Scanning: {local_folder}"
    )

    if not os.path.exists(local_folder):

        print(
            f"WARNING: Folder not found: {local_folder}"
        )

        return

    file_count = 0

    # Walk through all files and subfolders
    for root, directories, files in os.walk(local_folder):

        for file_name in files:

            local_path = os.path.join(
                root,
                file_name
            )

            upload_file(
                drive,
                local_path,
                drive_folder_id
            )

            file_count += 1

    print(
        f"Finished folder: {os.path.basename(local_folder)}"
    )

    print(
        f"Files checked: {file_count}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("JAN PROJECT → GOOGLE DRIVE")
    print("=" * 60)
    print()

    # --------------------------------------------------------
    # Check project folder
    # --------------------------------------------------------

    if not os.path.exists(PROJECT_FOLDER):

        print(
            "ERROR: priority_checker project folder was not found."
        )

        print(
            f"Expected location:\n{PROJECT_FOLDER}"
        )

        return

    print(
        f"Project folder:\n{PROJECT_FOLDER}"
    )

    print()

    # --------------------------------------------------------
    # Connect to Google Drive
    # --------------------------------------------------------

    drive = connect_to_drive()

    print()

    # --------------------------------------------------------
    # Find/create JAN Project folder
    # --------------------------------------------------------

    jan_project_id = find_or_create_folder(
        drive,
        DRIVE_PROJECT_NAME
    )

    print()

    print(
        f"Drive destination: {DRIVE_PROJECT_NAME}"
    )

    print()

    # --------------------------------------------------------
    # Upload only selected project folders
    # --------------------------------------------------------

    for folder_name in FOLDERS_TO_UPLOAD:

        local_folder = os.path.join(
            PROJECT_FOLDER,
            folder_name
        )

        print()
        print("-" * 60)
        print(f"PROCESSING: {folder_name}")
        print("-" * 60)

        # Create corresponding folder in Drive
        drive_folder_id = find_or_create_folder(
            drive,
            folder_name,
            jan_project_id
        )

        # Upload files
        upload_folder(
            drive,
            local_folder,
            drive_folder_id
        )

    # --------------------------------------------------------
    # Finished
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("JAN PROJECT UPLOAD COMPLETE!")
    print("=" * 60)
    print()

    print("Google Drive structure:")
    print()
    print("JAN Project/")
    print("├── input/")
    print("├── processed/")
    print("└── output/")
    print()


# ============================================================
# RUN PROGRAM
# ============================================================

if __name__ == "__main__":
    main()