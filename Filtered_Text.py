import re
import pdfplumber
import anthropic
import logging
import json 

# Hide pdfminer warnings
logging.getLogger("pdfminer").setLevel(logging.ERROR)


def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
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


def call_claude_api(cleaned_text, api_key):
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""
You are a data extraction assistant. Extract the following student details from the text and return a clean JSON object:
Fields: Full Name, Date of Birth,  Nationality, Address, Mobile Numbers, Emails, Final GPA, IELTS Score, School Name, Graduation Date.

Text:
\"\"\"
{cleaned_text}
\"\"\"

Return **only** JSON.
"""

    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",  # Using the latest Claude model
            max_tokens=1000,
            temperature=0.2,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.content[0].text
    except Exception as e:
        print(f"Error calling Claude API: {e}")
        return None


# === Main block ===
if __name__ == "__main__":
    pdf_path = "C:\\Users\\asank\\Downloads\\Leena Laith A Algoaz.pdf"
    api_key = "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"  # Replace with your actual Anthropic API key

    raw_text = extract_text_from_pdf(pdf_path)
    no_arabic = remove_arabic_text(raw_text)
    cleaned_text = clean_text(no_arabic)

    print("\nSending to Claude...\n")
    structured_info = call_claude_api(cleaned_text, api_key)

    if structured_info:
        print("\nStructured Student Info (JSON):\n")
        print(structured_info)