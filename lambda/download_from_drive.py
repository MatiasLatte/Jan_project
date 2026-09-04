import os
import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


# ============================================================
# SETTINGS
# ============================================================

LAMBDA_TMP = os.environ.get(
    "LAMBDA_TMP",
    "/tmp/jan_project"
)

SERVICE_ACCOUNT_FILE = os.path.join(
    os.path.dirname(__file__),
    "service_account.json"
)

DRIVE_PROJECT_NAME = os.environ.get(
    "GOOGLE_DRIVE_PROJECT_FOLDER",
    "JAN Project"
)

DRIVE_INPUT_FOLDER_NAME = os.environ.get(
    "GOOGLE_DRIVE_INPUT_FOLDER",
    "input"
)

LOCAL_INPUT_FOLDER = os.path.join(
    LAMBDA_TMP,
    "queue"
)

SCOPES = [
    "https://www.googleapis.com/auth/drive"
]


# ============================================================
# ESCAPE GOOGLE DRIVE QUERY
# ============================================================

def escape_drive_query(value):
    """
    Safely escape a value used inside a Google Drive query.
    """

    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("'", "\\'")
    )


# ============================================================
# CONNECT TO GOOGLE DRIVE
# ============================================================

def connect_to_drive():
    """
    Connect to Google Drive using the service account.
    """

    if not os.path.exists(SERVICE_ACCOUNT_FILE):

        raise FileNotFoundError(
            "Google Drive service account file was not found: "
            f"{SERVICE_ACCOUNT_FILE}"
        )

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

    If parent_id is supplied, only search inside that
    parent folder.
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

    print()
    print(
        f"Searching Drive folder: {folder_name}"
    )

    if parent_id:

        print(
            f"Parent folder ID: {parent_id}"
        )

    results = drive.files().list(
        q=query,
        spaces="drive",
        fields="files(id,name,parents)"
    ).execute()

    folders = results.get(
        "files",
        []
    )

    if not folders:

        print(
            f"Folder not found: {folder_name}"
        )

        return None

    if len(folders) > 1:

        print(
            f"WARNING: Found {len(folders)} "
            f"folders named '{folder_name}'."
        )

        print(
            "Using the first matching folder."
        )

    folder = folders[0]

    print(
        f"Found folder: {folder['name']}"
    )

    print(
        f"Folder ID: {folder['id']}"
    )

    return folder["id"]


# ============================================================
# FIND ALL PDF FILES
# ============================================================

def find_pdfs(
    drive,
    folder_id
):
    """
    Find ALL PDF files directly inside a Drive folder.

    Handles Drive pagination so files are not accidentally
    limited to the first page.
    """

    query = (
        f"'{folder_id}' in parents "
        "and mimeType = 'application/pdf' "
        "and trashed = false"
    )

    files = []

    page_token = None
    page_number = 0

    while True:

        page_number += 1

        print(
            f"Reading Google Drive PDF page "
            f"{page_number}..."
        )

        results = drive.files().list(
            q=query,
            spaces="drive",
            pageSize=1000,
            orderBy="name",
            fields=(
                "nextPageToken,"
                "files("
                "id,"
                "name,"
                "size,"
                "mimeType,"
                "parents,"
                "trashed"
                ")"
            ),
            pageToken=page_token
        ).execute()

        page_files = results.get(
            "files",
            []
        )

        print(
            f"  PDFs returned on page: "
            f"{len(page_files)}"
        )

        files.extend(
            page_files
        )

        page_token = results.get(
            "nextPageToken"
        )

        if not page_token:

            break

    # --------------------------------------------------------
    # Remove accidental duplicate Drive IDs
    # --------------------------------------------------------

    unique_files = []
    seen_ids = set()

    for pdf in files:

        file_id = pdf.get("id")

        if not file_id:
            continue

        if file_id in seen_ids:
            continue

        seen_ids.add(
            file_id
        )

        unique_files.append(
            pdf
        )

    # --------------------------------------------------------
    # Sort by filename
    # --------------------------------------------------------

    unique_files.sort(
        key=lambda item: (
            str(
                item.get(
                    "name",
                    ""
                )
            ).lower()
        )
    )

    return unique_files


# ============================================================
# CLEAN LOCAL QUEUE
# ============================================================

def clean_local_queue():
    """
    Remove existing PDFs from the Lambda queue.

    This prevents stale files from previous runs from
    interfering with the current Drive download.
    """

    os.makedirs(
        LOCAL_INPUT_FOLDER,
        exist_ok=True
    )

    removed = 0

    for filename in os.listdir(
        LOCAL_INPUT_FOLDER
    ):

        path = os.path.join(
            LOCAL_INPUT_FOLDER,
            filename
        )

        if not os.path.isfile(path):
            continue

        if filename.lower().endswith(
            ".pdf"
        ):

            try:

                os.remove(
                    path
                )

                removed += 1

            except Exception as error:

                print(
                    f"WARNING: Could not remove "
                    f"{filename}: {error}"
                )

    print(
        f"Cleaned local PDF queue: "
        f"{removed} old PDF(s) removed."
    )

    return removed


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
    Download one PDF from Google Drive.
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
                    f"Downloading "
                    f"{file_name}: "
                    f"{progress}%"
                )

    # --------------------------------------------------------
    # Verify downloaded file
    # --------------------------------------------------------

    if not os.path.exists(
        destination
    ):

        raise RuntimeError(
            f"Download completed but file "
            f"does not exist: {destination}"
        )

    file_size = os.path.getsize(
        destination
    )

    if file_size <= 0:

        raise RuntimeError(
            f"Downloaded PDF is empty: "
            f"{file_name}"
        )

    print(
        f"Downloaded successfully: "
        f"{file_name} "
        f"({file_size} bytes)"
    )


# ============================================================
# SAFE LOCAL FILENAME
# ============================================================

def make_unique_local_path(
    folder,
    filename
):
    """
    Create a unique local path.

    Normally Drive filenames are unique inside the folder.
    This protects against duplicate names just in case.
    """

    base_name = os.path.basename(
        filename
    )

    path = os.path.join(
        folder,
        base_name
    )

    if not os.path.exists(path):

        return path

    name, extension = os.path.splitext(
        base_name
    )

    counter = 2

    while True:

        candidate = os.path.join(
            folder,
            f"{name}_{counter}{extension}"
        )

        if not os.path.exists(
            candidate
        ):

            return candidate

        counter += 1


# ============================================================
# VERIFY LOCAL QUEUE
# ============================================================

def verify_local_queue():
    """
    Count PDFs actually present in the local queue.
    """

    if not os.path.exists(
        LOCAL_INPUT_FOLDER
    ):

        return []

    pdfs = []

    for filename in os.listdir(
        LOCAL_INPUT_FOLDER
    ):

        if filename.lower().endswith(
            ".pdf"
        ):

            pdfs.append(
                filename
            )

    pdfs.sort(
        key=lambda name: name.lower()
    )

    return pdfs


# ============================================================
# DOWNLOAD DRIVE INPUT
# ============================================================

def download_drive_input():
    """
    Download ALL PDFs from:

        Google Drive
            JAN Project
                input/

    into:

        /tmp/jan_project/queue/

    The queue is cleaned before every run.
    """

    print()
    print("=" * 70)
    print(
        "JAN PROJECT - GOOGLE DRIVE -> LAMBDA"
    )
    print("=" * 70)
    print()

    # --------------------------------------------------------
    # Prepare local queue
    # --------------------------------------------------------

    os.makedirs(
        LOCAL_INPUT_FOLDER,
        exist_ok=True
    )

    print(
        f"Lambda input folder:"
    )

    print(
        LOCAL_INPUT_FOLDER
    )

    print()

    # --------------------------------------------------------
    # IMPORTANT:
    # Remove stale PDFs from previous Lambda runs.
    # --------------------------------------------------------

    clean_local_queue()

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

    print()

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

    print()

    print(
        "Drive path:"
    )

    print(
        f"{DRIVE_PROJECT_NAME}/"
        f"{DRIVE_INPUT_FOLDER_NAME}"
    )

    print()

    # --------------------------------------------------------
    # Find ALL PDFs
    # --------------------------------------------------------

    pdf_files = find_pdfs(
        drive,
        input_folder_id
    )

    drive_total = len(
        pdf_files
    )

    print()
    print("=" * 70)
    print(
        "GOOGLE DRIVE PDF INVENTORY"
    )
    print("=" * 70)

    print(
        f"PDFs found in Drive: "
        f"{drive_total}"
    )

    if drive_total == 0:

        print()
        print(
            "WARNING: Google Drive input folder "
            "contains zero PDFs."
        )

        return {
            "downloaded": 0,
            "skipped": 0,
            "total": 0,
            "queue_count": 0,
            "drive_files": [],
        }

    print()

    for index, pdf in enumerate(
        pdf_files,
        start=1
    ):

        print(
            f"{index:>3}. "
            f"{pdf.get('name')}"
        )

    print()

    # ========================================================
    # DOWNLOAD ALL FILES
    # ========================================================

    downloaded = 0
    skipped = 0
    failed = 0

    failed_files = []

    print("=" * 70)
    print(
        "DOWNLOADING PDFs"
    )
    print("=" * 70)

    print()

    for index, pdf in enumerate(
        pdf_files,
        start=1
    ):

        file_id = pdf.get(
            "id"
        )

        file_name = pdf.get(
            "name"
        )

        if not file_id or not file_name:

            failed += 1

            failed_files.append(
                (
                    str(file_name),
                    "Missing Drive file ID or filename"
                )
            )

            continue

        local_path = make_unique_local_path(
            LOCAL_INPUT_FOLDER,
            file_name
        )

        print()
        print(
            f"[{index}/{drive_total}] "
            f"{file_name}"
        )

        try:

            download_pdf(
                drive,
                file_id,
                file_name,
                local_path
            )

            downloaded += 1

        except Exception as error:

            failed += 1

            failed_files.append(
                (
                    file_name,
                    str(error)
                )
            )

            print(
                f"ERROR downloading "
                f"{file_name}: {error}"
            )

    # ========================================================
    # VERIFY QUEUE
    # ========================================================

    local_pdfs = verify_local_queue()

    queue_count = len(
        local_pdfs
    )

    print()
    print("=" * 70)
    print(
        "LOCAL QUEUE VERIFICATION"
    )
    print("=" * 70)

    print(
        f"Drive PDFs found : {drive_total}"
    )

    print(
        f"Downloaded       : {downloaded}"
    )

    print(
        f"Failed           : {failed}"
    )

    print(
        f"PDFs in queue    : {queue_count}"
    )

    print()

    # --------------------------------------------------------
    # Detect discrepancy
    # --------------------------------------------------------

    if queue_count != downloaded:

        print(
            "WARNING: Number of PDFs in queue "
            "does not equal successful downloads."
        )

    # --------------------------------------------------------
    # Print failed files
    # --------------------------------------------------------

    if failed_files:

        print()
        print(
            "FAILED DOWNLOADS"
        )

        print(
            "-" * 70
        )

        for filename, reason in failed_files:

            print(
                f"{filename} --> {reason}"
            )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print(
        "DOWNLOAD COMPLETE"
    )
    print("=" * 70)

    print(
        f"Drive PDFs found : {drive_total}"
    )

    print(
        f"Downloaded       : {downloaded}"
    )

    print(
        f"Failed           : {failed}"
    )

    print(
        f"Queue PDFs       : {queue_count}"
    )

    print()

    return {
        "downloaded": downloaded,
        "skipped": skipped,
        "total": drive_total,
        "queue_count": queue_count,
        "failed": failed,
        "failed_files": failed_files,
        "drive_files": [
            pdf.get(
                "name"
            )
            for pdf in pdf_files
        ],
    }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    result = download_drive_input()

    print()
    print("=" * 70)
    print(
        "DOWNLOAD TEST RESULT"
    )
    print("=" * 70)

    print(
        result
    )