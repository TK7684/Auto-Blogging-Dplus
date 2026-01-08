import pypdf
import os

pdf_path = r"C:\Users\ttapk\PycharmProjects\pythonProject\Auto-Blogging-DPLUS\Products Data\คู่มือการโฆษณาเครื่องสำอางค์ ฉบับปรับปรุง ปี 67.pdf"
output_path = "compliance_text.txt"

try:
    reader = pypdf.PdfReader(pdf_path)
    with open(output_path, "w", encoding="utf-8") as f:
        for page in reader.pages:
            text = page.extract_text()
            f.write(text + "\n")
    print(f"Successfully extracted text to {output_path}")
except ImportError:
    print("Error: pypdf is not installed.")
except Exception as e:
    print(f"Error: {e}")
