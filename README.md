# UK-Education

## 🧠 Project Overview

This project automates the extraction and processing of student information from PDF files and simulates an online college application submission using browser automation.

It combines:
- **Text Extraction** with `pdfplumber`
- **Text Cleaning & Filtering** (removal of Arabic, symbols, and noise)
- **AI-Powered Structuring** using Anthropic's Claude API
- **Browser Automation** via Playwright (Chromium headless or visible mode)

---

## 🎯 Objectives

- ✅ Automatically extract key student information from exported/scanned documents (PDFs)
- ✅ Convert unstructured student data into structured JSON format
- ✅ Automatically fill a web application form using Playwright
- 🚫 Avoid manual data entry, especially in repetitive admission tasks

---

## ⚙️ Pipeline Architecture

```mermaid
flowchart TD
    A[PDF Upload] --> B[Extract Text with pdfplumber]
    B --> C[Clean & Filter Text]
    C --> D[Send to Claude API]
    D --> E[Get JSON Response]
    E --> F[Use Playwright to Auto-Fill Web Form]


## 🔧 Requirements

- Python 3.8+
- `anthropic`
- `pdfplumber`
- 're'
- 'OpenAi'
- 'Playwright'

Install with:
pip install anthropic
pip install pdfplumber
pip install openai
pip install playwright
playwright install

```bash
pip install -r requirements.txt
