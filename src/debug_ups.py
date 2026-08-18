import pdfplumber

pdf_path = "input/6f3be62b-7003-4c07-aebe-bfa15b3eb368.pdf"

with pdfplumber.open(pdf_path) as pdf:

    print(f"Pages: {len(pdf.pages)}")

    for i, page in enumerate(pdf.pages, start=1):

        print("\n" + "=" * 80)
        print(f"PAGE {i}")
        print("=" * 80)

        text = page.extract_text()

        if text:
            print(text)
        else:
            print("No text extracted")