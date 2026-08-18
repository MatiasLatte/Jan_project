import pdfplumber

pdf_path = "input/12.99999.10030.939569296.XXXXX9869.000178.pdf"

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