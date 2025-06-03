import re
import pdfplumber
import anthropic
import logging
import json
from Extract_Text import extract_text_from_pdf
from Extract_Text import remove_arabic_text# Hide pdfminer warnings
from Extract_Text import clean_text# Hide pdfminer warnings
from playwright.sync_api import sync_playwright

logging.getLogger("pdfminer").setLevel(logging.ERROR)


def call_claude_api(cleaned_text, api_key):
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""
You are a data extraction assistant. Extract the following student details from the text and return a clean JSON object:
Fields: Full Name, Date of Birth, Nationality, Address, Mobile Numbers, Emails, Final GPA, IELTS Score, School Name, Graduation Date.

Text:
\"\"\"
{cleaned_text}
\"\"\"

Return **only** JSON.
"""

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # Updated model name
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


def parse_student_info(json_response):
    """Parse JSON response and extract individual string variables"""
    try:
        # Clean the response in case there are markdown code blocks
        cleaned_response = json_response.strip()
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()

        # Parse JSON
        data = json.loads(cleaned_response)

        # Extract individual fields as strings
        full_name = str(data.get("Full Name", "")).strip()
        date_of_birth = str(data.get("Date of Birth", "")).strip()
        nationality = str(data.get("Nationality", "")).strip()
        address = str(data.get("Address", "")).strip()
        mobile_numbers = str(data.get("Mobile Numbers", "")).strip()
        emails = str(data.get("Emails", "")).strip()
        final_gpa = str(data.get("Final GPA", "")).strip()
        ielts_score = str(data.get("IELTS Score", "")).strip()
        school_name = str(data.get("School Name", "")).strip()
        graduation_date = str(data.get("Graduation Date", "")).strip()

        return {
            "full_name": full_name,
            "date_of_birth": date_of_birth,
            "nationality": nationality,
            "address": address,
            "mobile_numbers": mobile_numbers,
            "emails": emails,
            "final_gpa": final_gpa,
            "ielts_score": ielts_score,
            "school_name": school_name,
            "graduation_date": graduation_date
        }

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Raw response: {json_response}")
        return None
    except Exception as e:
        print(f"Error extracting student info: {e}")
        return None


# === Main block ===
if __name__ == "__main__":
    pdf_path = "C:\\Users\\asank\\Downloads\\Leena Laith A Algoaz.pdf"
    api_key = "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"  # Replace with your actual Claude API key

    raw_text = extract_text_from_pdf(pdf_path)
    no_arabic = remove_arabic_text(raw_text)
    cleaned_text = clean_text(no_arabic)

    print("\nSending to Claude...\n")
    structured_info = call_claude_api(cleaned_text, api_key)

    if structured_info:
        print("\nRaw JSON Response:\n")
        print(structured_info)

        # Parse the JSON and extract string variables
        student_data = parse_student_info(structured_info)

        if student_data:
            print("\n" + "=" * 50)
            print("EXTRACTED STRING VARIABLES:")
            print("=" * 50)

            # Individual string variables
            full_name = student_data["full_name"]
            date_of_birth = student_data["date_of_birth"]
            nationality = student_data["nationality"]
            address = student_data["address"]
            mobile_numbers = student_data["mobile_numbers"]
            emails = student_data["emails"]
            final_gpa = student_data["final_gpa"]
            ielts_score = student_data["ielts_score"]
            school_name = student_data["school_name"]
            graduation_date = student_data["graduation_date"]




            print(f"Full Name: '{full_name}'")
            print(f"Date of Birth: '{date_of_birth}'")
            print(f"Nationality: '{nationality}'")
            print(f"Address: '{address}'")
            print(f"Mobile Numbers: '{mobile_numbers}'")
            print(f"Emails: '{emails}'")
            print(f"Final GPA: '{final_gpa}'")
            print(f"IELTS Score: '{ielts_score}'")
            print(f"School Name: '{school_name}'")
            print(f"Graduation Date: '{graduation_date}'")

            #Automation
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)  # set headless=True to run without UI
                page = browser.new_page()

                # Open the application page
                page.goto("https://kicpathways.formstack.com/forms/uk_application_combined")

                # Wait for and click the radio button
                page.wait_for_selector("#field167775915_3")
                page.click("#field167775915_3")

                # Wait for the text input and type
                page.wait_for_selector("#field167775918")
                page.fill("#field167775918", "UK Education Services")

                page.wait_for_selector("#field167775921-first")
                page.fill("#field167775921-first", "rama")

                page.wait_for_selector("#field167775922")
                page.fill("#field167775922", "rama@ukeducationservices.com")

                page.wait_for_selector("#field167775936")
                page.fill("#field167775936", full_name)

                page.wait_for_selector("#field167775945")
                page.fill("#field167775945", emails)

                page.wait_for_selector("#fsNextButton5813211")
                page.click("#fsNextButton5813211")

                page.wait_for_selector("#field167776176")
                page.fill("#field167776176", school_name)

                page.wait_for_selector("#fsNextButton5813211")
                page.click("#fsNextButton5813211")

                page.wait_for_selector("#field167776220")
                page.fill("#field167776220", mobile_numbers)

                page.wait_for_timeout(2000)  # waits 2 seconds (milliseconds!)

                

                # Keep browser open or close it
                # browser.close()
