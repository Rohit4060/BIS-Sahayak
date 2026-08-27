"""
Quick test: does PyMuPDF extract Hindi text correctly from our sample PDF,
where pdfplumber failed? Run this before touching the real ingestion script.
"""
import sys
import fitz  # PyMuPDF

pdf_path = sys.argv[1] if len(sys.argv) > 1 else "../data/raw/IS_302_Part1_Household_Appliances_Safety.pdf"

doc = fitz.open(pdf_path)
page1 = doc[0]
text = page1.get_text()

print("----- PyMuPDF extraction of page 1 -----")
print(text)
print("-----------------------------------------")
doc.close()