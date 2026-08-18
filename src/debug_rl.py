import pdfplumber

pdf_path = "input/RL IAJ1866456.pdf"

with pdfplumber.open(pdf_path) as pdf:

    print(f"Number of pages: {len(pdf.pages)}")

    for i, page in enumerate(pdf.pages, start=1):

        print("\n" + "=" * 80)
        print(f"PAGE {i}")
        print("=" * 80)

        text = page.extract_text()

        if text:
            print(text)
        else:
            print("No text extracted")
