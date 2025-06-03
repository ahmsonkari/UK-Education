# UK-Education

# 🧾 Student Info Extractor from PDF

This Python script automates the extraction of structured student information from scanned or exported PDF documents. It leverages `pdfplumber` to read PDF text, cleans it, and uses **Claude AI (Anthropic)** to convert unstructured text into a structured JSON format.

---

## 📌 Use Case

This tool is designed to simplify the process of extracting key student application details such as:
- Full Name
- Date of Birth
- Nationality
- Address
- Contact Info (Mobile, Email)
- Academic Records (GPA, IELTS Score)
- School Information

It is ideal for **automated application pipelines**, data analysis, or generating reports from PDFs.

---

## 🧠 How It Works

1. ✅ **Reads the PDF** using `pdfplumber`
2. 🧹 **Cleans and filters the text**, removing Arabic and non-ASCII characters
3. 🤖 **Sends the text to Claude** using Anthropic API
4. 🧾 **Prints each field individually** from the returned JSON

---

## 🔧 Requirements

- Python 3.8+
- `anthropic`
- `pdfplumber`

Install with:

```bash
pip install -r requirements.txt
