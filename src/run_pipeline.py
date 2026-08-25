import os
import subprocess
import sys


# ============================================================
# SETTINGS
# ============================================================

PROJECT_FOLDER = os.path.expanduser(
    "~/Documents/priority1_checker"
)

SRC_FOLDER = os.path.join(
    PROJECT_FOLDER,
    "src"
)


# ============================================================
# RUN A PYTHON SCRIPT
# ============================================================

def run_script(script_name):

    script_path = os.path.join(
        SRC_FOLDER,
        script_name
    )

    print()
    print("=" * 70)
    print(f"RUNNING: {script_name}")
    print("=" * 70)
    print()

    if not os.path.exists(script_path):

        print(
            f"ERROR: Script not found: {script_path}"
        )

        return False

    result = subprocess.run(
        [sys.executable, script_path],
        cwd=PROJECT_FOLDER
    )

    if result.returncode != 0:

        print()
        print("=" * 70)
        print(f"❌ {script_name} FAILED")
        print("=" * 70)

        return False

    print()
    print("=" * 70)
    print(f"✅ {script_name} COMPLETED")
    print("=" * 70)

    return True


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():

    print()
    print("=" * 70)
    print("JAN PDF AUTOMATION PIPELINE")
    print("=" * 70)

    print()
    print(
        f"Project:\n{PROJECT_FOLDER}"
    )

    print()

    # --------------------------------------------------------
    # Verify project exists
    # --------------------------------------------------------

    if not os.path.exists(PROJECT_FOLDER):

        print(
            "❌ Project folder not found."
        )

        print(
            PROJECT_FOLDER
        )

        sys.exit(1)


    # ========================================================
    # STEP 1
    # Google Drive → input
    # ========================================================

    if not run_script(
        "download_from_drive.py"
    ):

        print()
        print(
            "Pipeline stopped during Google Drive download."
        )

        sys.exit(1)


    # ========================================================
    # STEP 2
    # input → queue
    # ========================================================

    if not run_script(
        "prepare_queue.py"
    ):

        print()
        print(
            "Pipeline stopped while preparing the queue."
        )

        sys.exit(1)


    # ========================================================
    # STEP 3
    # queue → processing
    # ========================================================

    if not run_script(
        "main.py"
    ):

        print()
        print(
            "Pipeline stopped during PDF processing."
        )

        sys.exit(1)


    # ========================================================
    # COMPLETE
    # ========================================================

    print()
    print("=" * 70)
    print("✅ JAN PDF AUTOMATION PIPELINE COMPLETE")
    print("=" * 70)

    print()
    print("Workflow completed:")
    print()
    print("Google Drive")
    print("     ↓")
    print("JAN Project/input")
    print("     ↓")
    print("local input/")
    print("     ↓")
    print("queue/")
    print("     ↓")
    print("main.py")
    print("     ↓")
    print("processed/")
    print("     ↓")
    print("output/")
    print()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()