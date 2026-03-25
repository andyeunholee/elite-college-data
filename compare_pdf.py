import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

pdf_path = "CommonApp-Application-Requirement.pdf"

# The 18 colleges from the image:
colleges = [
    "Princeton University", "Massachusetts Institute of Technology", "Harvard University", "Stanford University",
    "Yale University", "University of Pennsylvania", "University of Florida", "California Institute of Technology",
    "Duke University", "Johns Hopkins University", "Northwestern University", "Brown University",
    "University of Chicago", "Columbia University", "Cornell University", "University of California, Berkeley",
    "Rice University", "Dartmouth College"
]

print("Uploading PDF to Gemini...")
uploaded_file = client.files.upload(file=pdf_path)

prompt = f"""
You are an expert data extractor. I have provided the CommonApp Application Requirements PDF.
Based STRICTLY on this PDF, extract the following information for these 18 colleges:
{json.dumps(colleges, indent=2)}

For each college, extract:
1. Standardized Test Policy (e.g., "Always Required", "Sometimes Required", "Never Required", etc.)
2. Early Decision (ED) Deadline (MM/DD)
3. Early Action (EA) or Restrictive Early Action (REA) Deadline (MM/DD)

Return exactly a JSON array of objects with keys:
- "name" (college name)
- "test_policy_in_pdf"
- "ed_deadline_in_pdf"
- "ea_or_rea_deadline_in_pdf"

Return ONLY the JSON array.
"""

print("Requesting extraction from Gemini 2.5 Flash...")
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[uploaded_file, prompt],
    config=types.GenerateContentConfig(response_mime_type="application/json")
)

print("\n--- Extracted PDF Data ---")
try:
    data = json.loads(response.text)
    for row in data:
        print(f"[{row['name']}] Test Policy: {row.get('test_policy_in_pdf')}, ED: {row.get('ed_deadline_in_pdf')}, EA/REA: {row.get('ea_or_rea_deadline_in_pdf')}")
except Exception as e:
    print("Failed to parse JSON:", e)
    print("Raw output:", response.text)

print("\nCleaning up file...")
client.files.delete(name=uploaded_file.name)
print("Done.")
