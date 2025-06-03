import pdfplumber
import logging
import re
# Hide pdfminer warnings
logging.getLogger("pdfminer").setLevel(logging.ERROR)

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def remove_arabic_text(text):
    arabic_pattern = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+")
    return re.sub(arabic_pattern, "", text)


def clean_text(text):
    # Remove extra symbols, multiple spaces, etc.
    text = re.sub(r"[^\x00-\x7F]+", " ", text)  # Remove non-ASCII (just in case)
    text = re.sub(r"[!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

if __name__ == "__main__":
    pdf_path = r"C:\Users\asank\Downloads\Leena Laith A Algoaz.pdf"
    extracted_text = extract_text_from_pdf(pdf_path)
    print(extracted_text)
