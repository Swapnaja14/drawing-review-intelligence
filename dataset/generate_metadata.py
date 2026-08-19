from pathlib import Path
import csv


# =========================================================
# PATH CONFIGURATION
# =========================================================

# Folder containing this script
BASE_DIR = Path(__file__).resolve().parent

# Folder containing categorized PDF files
DATASET_DIR = BASE_DIR / "raw_drawings"

# Output CSV
OUTPUT_FILE = BASE_DIR / "metadata" / "drawing_metadata.csv"


# =========================================================
# CATEGORY MAPPING
# =========================================================

CATEGORIES = {
    "Electrical Engineering": (1, "Electrical Engineering"),
    "GPD": (2, "GPD"),
    "Pipe Support Engineering": (3, "Pipe Support Engineering"),
    "Piping Engineering": (4, "Piping Engineering"),
    "Plakon": (5, "Plakon"),
    "Structural & Physical Design": (6, "Structural & Physical Design"),
    "System Engineering": (7, "System Engineering"),
}

# =========================================================
# GENERATE METADATA
# =========================================================

def generate_metadata():

    print("=" * 60)
    print("DRAWING METADATA GENERATOR")
    print("=" * 60)
    print()

    print("Dataset directory:")
    print(DATASET_DIR)
    print()

    # Check raw_drawings folder
    if not DATASET_DIR.exists():

        print("ERROR:")
        print("raw_drawings folder was not found.")
        print()

        print("Expected location:")
        print(DATASET_DIR)

        return

    rows = []

    drawing_number = 1

    # -----------------------------------------------------
    # Process each category
    # -----------------------------------------------------

    for folder_name, (category_id, category_name) in CATEGORIES.items():

        category_folder = DATASET_DIR / folder_name

        print(f"Processing: {category_name}")

        if not category_folder.exists():

            print(f"  WARNING: Folder not found:")
            print(f"  {category_folder}")
            print()

            continue

        # Find PDFs
        pdf_files = sorted(
            category_folder.glob("*.pdf")
        )

        print(f"  PDFs found: {len(pdf_files)}")

        # Create metadata row for every PDF
        for pdf_file in pdf_files:

            drawing_id = f"DR{drawing_number:03d}"

            rows.append({
                "Drawing ID": drawing_id,
                "File Name": pdf_file.name,
                "Category ID": category_id,
                "Category Name": category_name,
                "PDF Path": str(
                    pdf_file.relative_to(BASE_DIR)
                ),
                "Pages": "",
                "Drawing Type": "",
                "Source": "",
                "Status": "Pending"
            })

            drawing_number += 1

        print()

    # -----------------------------------------------------
    # Create metadata directory
    # -----------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # -----------------------------------------------------
    # Write CSV
    # -----------------------------------------------------

    fieldnames = [
        "Drawing ID",
        "File Name",
        "Category ID",
        "Category Name",
        "PDF Path",
        "Pages",
        "Drawing Type",
        "Source",
        "Status"
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)

    # -----------------------------------------------------
    # Final result
    # -----------------------------------------------------

    print("=" * 60)
    print("METADATA GENERATION COMPLETED")
    print("=" * 60)
    print()

    print(f"Total PDFs found: {len(rows)}")
    print()

    print("CSV generated at:")
    print(OUTPUT_FILE)
    print()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    generate_metadata()