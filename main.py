from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import re
import pdfplumber
import anthropic
import logging
import json
import tempfile
import asyncio
from playwright.async_api import async_playwright
import uvicorn
from pathlib import Path
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Student Info Extractor API")

class FillFormRequest(BaseModel):
    student_data: Dict[str, Any]
    agent_name: str

# === Utility Functions ===
def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file"""
    text = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to extract text from PDF: {str(e)}")


def remove_arabic_text(text):
    """Remove Arabic text from content"""
    arabic_pattern = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+")
    return re.sub(arabic_pattern, "", text)


def clean_text(text):
    """Clean and normalize text"""
    text = re.sub(r"[^\x00-\x7F]+", " ", text)  # Remove non-ASCII
    text = re.sub(r"[!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def call_claude_api(cleaned_text: str, api_key: str):
    """Call Claude API to extract student information"""
    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""
You are a data extraction assistant. 
Note1:Dates attended should be like EX:09/2023-06/2024
Note2: Date of Birth should be like EX:29/06/2004
Note3:IELTS date should be like EX: jun 2024
Note4: School region choose the country Example Saudi Arabia
Note5: gender is either 'M' or 'F'
Note6: don't save them in parantases like () [] "" '' save them as they are

 Extract the following student details from the text and return a clean JSON object:
Fields: First name,Middle name,Last name,Gender,Date of Birth, Nationality,Place of Birth, Address,Address Country,Address City ,
Mobile Numbers, Emails
,  IELTS Score,IELTS Date, Name of Qualification ,School Name, School region ,Dates attended

Text:
\"\"\"{cleaned_text}\"\"\"

Return only JSON.
"""
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        raise HTTPException(status_code=500, detail=f"Claude API Error: {str(e)}")


def parse_student_info(json_response: str):
    """Parse JSON response from Claude API"""
    try:
        cleaned_response = json_response.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned_response)
        
        # Normalize keys and ensure all values are strings
        normalized_data = {}
        for k, v in data.items():
            key = k.lower().replace(" ", "_")
            normalized_data[key] = str(v).strip() if v else ""
        
        return normalized_data
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Raw response: {json_response}")
        raise HTTPException(status_code=400, detail=f"Failed to parse JSON response: {str(e)}")
    except Exception as e:
        logger.error(f"Parse error: {e}")
        raise HTTPException(status_code=400, detail=f"JSON Parse Error: {str(e)}")


async def fill_form_async(data: dict, agent_name: str):
    """Fill form using Playwright with proper error handling"""
    try:
        async with async_playwright() as p:
            # Launch browser with proper configuration for server environment
            browser = await p.chromium.launch(
                headless=True,  # CHANGED: Set to True for server environments
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-dev-tools',
                    '--no-zygote',
                    '--single-process',
                    '--disable-web-security',  # Added for form automation
                    '--disable-features=VizDisplayCompositor',  # Added for stability
                ]
            )

            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            page = await context.new_page()

            # Add console logging for debugging
            page.on("console", lambda msg: logger.info(f"Browser console: {msg.text}"))
            page.on("pageerror", lambda error: logger.error(f"Page error: {error}"))

            try:
                logger.info("Navigating to form...")
                await page.goto(
                    "https://kicpathways.formstack.com/forms/uk_application_combined",
                    wait_until="networkidle",
                    timeout=60000  # Increased timeout
                )

                logger.info("Filling first page...")
                # First page
                await page.wait_for_selector("#field167775915_3", timeout=10000)
                await page.click("#field167775915_3")

                await page.wait_for_selector("#field167775918", timeout=10000)
                await page.fill("#field167775918", "UK Education Services")

                await page.wait_for_selector("#field167775921-first", timeout=10000)
                await page.fill("#field167775921-first", agent_name)

                await page.wait_for_selector("#field167775921-last", timeout=10000)
                await page.fill("#field167775921-last", ".")

                await page.wait_for_selector("#field167775922", timeout=10000)
                await page.fill("#field167775922", f"{agent_name}@ukeducationservices.com")

                await page.select_option("#field167775920", index=202)

                await page.wait_for_selector("#field167775936", timeout=10000)
                await page.fill("#field167775936", data.get("first_name", "") + " " + data.get("middle_name", ""))

                await page.wait_for_selector("#field167775937", timeout=10000)
                await page.fill("#field167775937", data.get("last_name", ""))

                await page.select_option("#field167775938", data.get("nationality"))
                
                await page.wait_for_selector("#field167775945", timeout=10000)
                await page.fill("#field167775945", data.get("emails", ""))

                await page.wait_for_selector("#field167775941_2", timeout=10000)
                await page.click("#field167775941_2")

                await page.wait_for_selector("#field167775943_2", timeout=10000)
                await page.click("#field167775943_2")

                # Click next button
                await page.wait_for_selector("#fsNextButton5813211", timeout=10000)
                await page.click("#fsNextButton5813211")

                logger.info("Filling second page...")
                # Second page
                await page.wait_for_selector("#field167776174", timeout=10000)
                await page.fill("#field167776174", data.get("name_of_qualification", ""))

                await page.wait_for_selector("#field167776176", timeout=10000)
                await page.fill("#field167776176", data.get("school_name", ""))

                await page.wait_for_selector("#field167776175", timeout=10000)
                await page.fill("#field167776175", data.get("dates_attended", ""))

                await page.select_option("#field167776177", data.get("school_region"))

                if data.get("ielts_score") is None:
                    await page.click("#field167776190_2")
                else:
                    await page.click("#field167776190_1")
                    await page.wait_for_selector("#field167776191_1", timeout=10000)
                    await page.click("#field167776191_1")

                await page.wait_for_selector("#fsNextButton5813211", timeout=10000)
                await page.click("#fsNextButton5813211")

                logger.info("Filling third page...")
                # Third page
                await page.wait_for_selector("#field167776220", timeout=10000)
                await page.fill("#field167776220", data.get("mobile_numbers", ""))

                await page.wait_for_selector("#field167776218-\\*", timeout=10000)
                await page.fill("#field167776218-\\*", data.get("date_of_birth"))

                await page.click("#field167776213_2")
                await page.click("#field167776215_2")

                await page.select_option("#field167776233", data.get("address_country"))

                await page.wait_for_selector("#field167776234", timeout=10000)
                await page.fill("#field167776234", data.get("address", ""))

                await page.wait_for_selector("#field167776236", timeout=10000)
                await page.fill("#field167776236", data.get("address_city", ""))

                await page.click("#field167776223_3")
                await page.click("#field167776229_2")
                await page.click("#field167776240_1")

                logger.info("Filling fourth page...")
                # Fourth page
                await page.click("#fsNextButton5813211")
                await page.click("#field167776264_2")
                await page.click("#field167776268_2")

                # Copy Link
                await page.wait_for_selector("#fsForm5813211 > button", timeout=10000)
                await page.click("#fsForm5813211 > button")

                await page.wait_for_selector('.StyledDialogActions-sc-1m3qehg-0.dWImUC', timeout=10000)
                await page.click('button.StyledDialogButton-sc-1hp70zu-0.fPMYgh')

                selector = 'body > div > form > div.fs-external-module__content.fs--grid-4-8 > div > main > div.fs-module-main__message.fs-module-main__message--initial.fs--mb0 > p:nth-child(3) > a'
                await page.wait_for_selector(selector, timeout=10000)
                element_text = await page.locator(selector).text_content()

                print(f"Element text: {element_text}")
                logger.info(f"Element text: {element_text}")

                await page.wait_for_timeout(2000)

                logger.info("Form filling completed successfully")
                return {"status": "success", "message": "Form filled successfully", "element_text": element_text}

            except Exception as e:
                logger.error(f"Form filling error: {e}")
                # Take screenshot for debugging (works in headless mode too)
                try:
                    screenshot_path = f"error_screenshot_{agent_name}_{int(asyncio.get_event_loop().time())}.png"
                    await page.screenshot(path=screenshot_path)
                    logger.info(f"Screenshot saved: {screenshot_path}")
                except Exception as screenshot_error:
                    logger.error(f"Failed to take screenshot: {screenshot_error}")
                raise e

            finally:
                await browser.close()

    except Exception as e:
        logger.error(f"Playwright error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Browser automation failed: {str(e)}. Make sure Playwright browsers are installed."
        )


# === API Endpoints ===
@app.get("/", response_class=HTMLResponse)
async def home():
    """Render the home page with the form"""
    return """
    <html>
        <head>
            <title>Student Info Extractor</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                form { display: flex; flex-direction: column; gap: 15px; }
                input, button { padding: 10px; font-size: 16px; }
                button { background-color: #4CAF50; color: white; border: none; cursor: pointer; border-radius: 5px; }
                button:hover { background-color: #45a049; }
                button:disabled { background-color: #cccccc; cursor: not-allowed; }
                .result { margin-top: 20px; padding: 15px; background-color: #f5f5f5; border-radius: 5px; }
                .error { color: red; }
                .success { color: green; }
                .loading { color: blue; }
                .highlight { background-color: #ffffcc; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #4CAF50; }
                pre { background-color: #f0f0f0; padding: 10px; border-radius: 3px; overflow-x: auto; }
            </style>
        </head>
        <body>
            <h1>📄 Student Info Extractor + Form Auto-Filler</h1>
            <form id="extractForm">
                <input type="password" name="api_key" placeholder="Claude API Key" required>
                <input type="text" name="agent_name" placeholder="Agent Name" required>
                <input type="file" name="pdf_file" accept=".pdf" required>
                <button type="submit">🔍 Extract Student Info</button>
            </form>
            <div id="result" class="result" style="display: none;"></div>

            <script>
                let extractedData = null;
                let agentName = null;

                document.getElementById('extractForm').addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const resultDiv = document.getElementById('result');
                    const submitBtn = e.target.querySelector('button[type="submit"]');

                    resultDiv.style.display = 'block';
                    resultDiv.innerHTML = '<p class="loading">Processing PDF...</p>';
                    submitBtn.disabled = true;

                    try {
                        const formData = new FormData();
                        formData.append('api_key', e.target.api_key.value);
                        formData.append('agent_name', e.target.agent_name.value);
                        formData.append('pdf_file', e.target.pdf_file.files[0]);

                        agentName = e.target.agent_name.value;

                        const response = await fetch('/extract', {
                            method: 'POST',
                            body: formData
                        });

                        const result = await response.json();

                        if (response.ok) {
                            extractedData = result;
                            resultDiv.innerHTML = `
                                <h3 class="success">✅ Extracted Data:</h3>
                                <pre>${JSON.stringify(result, null, 2)}</pre>
                                <button onclick="fillForm()" style="margin-top: 10px;">🤖 Fill Form Automatically</button>
                                <div id="fillFormResult"></div>
                            `;
                        } else {
                            resultDiv.innerHTML = `
                                <h3 class="error">❌ Error:</h3>
                                <p class="error">${result.detail || 'Unknown error occurred'}</p>
                            `;
                        }
                    } catch (error) {
                        console.error('Error:', error);
                        resultDiv.innerHTML = `
                            <h3 class="error">❌ Network Error:</h3>
                            <p class="error">${error.message}</p>
                        `;
                    } finally {
                        submitBtn.disabled = false;
                    }
                });

                async function fillForm() {
                    const fillResultDiv = document.getElementById('fillFormResult') || document.createElement('div');
                    fillResultDiv.id = 'fillFormResult';

                    if (!document.getElementById('fillFormResult')) {
                        document.getElementById('result').appendChild(fillResultDiv);
                    }

                    fillResultDiv.innerHTML = '<p class="loading">🚀 Launching browser and filling form...</p>';

                    try {
                        if (!extractedData) {
                            throw new Error('No student data found. Please extract information first.');
                        }

                        if (!agentName) {
                            throw new Error('Agent name not found. Please try extracting data again.');
                        }

                        const response = await fetch('/fill-form', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                student_data: extractedData,
                                agent_name: agentName
                            })
                        });

                        const result = await response.json();

                        if (response.ok) {
                            let successHtml = '<p class="success">✅ Browser launched successfully! Please complete any remaining steps manually.</p>';

                            // Display element text if available
                            if (result.element_text) {
                                successHtml += `
                                    <div class="highlight">
                                        <h4>🔗 Generated Link:</h4>
                                        <p><strong>Element Text:</strong> <code>${result.element_text}</code></p>
                                        <a href="${result.element_text}" target="_blank" style="color: #4CAF50; text-decoration: underline;">🔗 Open Link</a>
                                    </div>
                                `;
                            }

                            fillResultDiv.innerHTML = successHtml;
                        } else {
                            throw new Error(result.detail || 'Failed to launch browser');
                        }
                    } catch (error) {
                        console.error('Form fill error:', error);
                        fillResultDiv.innerHTML = `<p class="error">❌ Error: ${error.message}</p>`;
                    }
                }
            </script>
        </body>
    </html>
    """

@app.post("/extract")
async def extract_info(
        pdf_file: UploadFile = File(...),
        api_key: str = Form(...),
        agent_name: str = Form(...)
):
    """Extract student information from PDF"""
    pdf_path = None
    try:
        # Validate file type
        if not pdf_file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await pdf_file.read()
            tmp.write(content)
            pdf_path = tmp.name

        logger.info(f"Processing PDF: {pdf_file.filename}")
        
        # Process PDF
        raw_text = extract_text_from_pdf(pdf_path)
        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="No text found in PDF file")
            
        no_arabic = remove_arabic_text(raw_text)
        cleaned_text = clean_text(no_arabic)

        # Call Claude API
        json_response = await call_claude_api(cleaned_text, api_key)
        if not json_response:
            raise HTTPException(status_code=500, detail="No response from Claude API")

        # Parse response
        student_data = parse_student_info(json_response)
        
        logger.info("Data extraction completed successfully")
        return student_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")
    finally:
        # Clean up temporary file
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.unlink(pdf_path)
            except:
                pass


@app.post("/fill-form")
async def fill_form(request: FillFormRequest):
    """Launch browser and fill form with student data"""
    try:
        # Validate required fields
        required_fields = ['first_name', 'emails', 'school_name', 'mobile_numbers']
        missing_fields = []
        
        for field in required_fields:
            if field not in request.student_data or not str(request.student_data[field]).strip():
                missing_fields.append(field)
        
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {', '.join(missing_fields)}. Please make sure all fields were extracted correctly."
            )

        logger.info(f"Starting form automation for agent: {request.agent_name}")
        result = await fill_form_async(request.student_data, request.agent_name)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Form filling error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fill form: {str(e)}. Make sure Playwright browsers are installed (run 'playwright install')."
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running"}


# === Testing Functions ===
@app.post("/test-browser")
async def test_browser():
    """Test browser launch without form filling"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
    headless=True,  # Changed to True for production
    args=[
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-dev-tools',
        '--no-zygote',
        '--single-process',  # Important for Railway
    ]
)
            page = await browser.new_page()
            await page.goto("https://www.google.com")
            await page.wait_for_timeout(3000)
            await browser.close()
            return {"status": "success", "message": "Browser test passed"}
    except Exception as e:
        logger.error(f"Browser test failed: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

