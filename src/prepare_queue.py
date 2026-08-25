import os
import shutil


# ============================================================
# SETTINGS
# ============================================================

PROJECT_FOLDER = os.path.expanduser(
    "~/Documents/priority1_checker"
)

INPUT_FOLDER = os.path.join(
    PROJECT_FOLDER,
    "input"
)

QUEUE_FOLDER = os.path.join(
    PROJECT_FOLDER,
    "queue"
)


# ============================================================
# PREPARE FOLDERS
# ============================================================

os.makedirs(
    INPUT_FOLDER,
    exist_ok=True
)

os.makedirs(
    QUEUE_FOLDER,
    exist_ok=True
)


# ============================================================
# MOVE PDFs FROM INPUT → QUEUE
# ============================================================

print("=" * 60)
print("PREPARING PDF QUEUE")
print("=" * 60)

pdf_files = [
    file_name
    for file_name in os.listdir(INPUT_FOLDER)
    if file_name.lower().endswith(".pdf")
]


if not pdf_files:

    print()
    print("No PDF files found in input.")
    print()

    exit()


print()
print(
    f"Found {len(pdf_files)} PDF(s) in input."
)
print()


moved = 0
skipped = 0


for file_name in pdf_files:

    source = os.path.join(
        INPUT_FOLDER,
        file_name
    )

    destination = os.path.join(
        QUEUE_FOLDER,
        file_name
    )

    # --------------------------------------------------------
    # Don't overwrite a PDF already in queue
    # --------------------------------------------------------

    if os.path.exists(destination):

        print(
            f"Already in queue, skipping: {file_name}"
        )

        skipped += 1

        continue

    # --------------------------------------------------------
    # Move PDF into queue
    # --------------------------------------------------------

    shutil.move(
        source,
        destination
    )

    print(
        f"Moved to queue: {file_name}"
    )

    moved += 1


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 60)
print("QUEUE PREPARATION COMPLETE")
print("=" * 60)

print(
    f"Moved   : {moved}"
)

print(
    f"Skipped : {skipped}"
)

print()
print(
    "Next step:"
)

print(
    "python src/main.py"
)

print()