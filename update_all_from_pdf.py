import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from college_lists import NATIONAL_UNIVERSITIES, LIBERAL_ARTS_COLLEGES

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
pdf_path = os.path.abspath("CommonApp-Application-Requirement.pdf")

all_colleges = [c["name"] for c in NATIONAL_UNIVERSITIES] + [c["name"] for c in LIBERAL_ARTS_COLLEGES]
batch_size = 50
batches = [all_colleges[i:i+batch_size] for i in range(0, len(all_colleges), batch_size)]

print("Uploading PDF to Gemini...")
uploaded_file = client.files.upload(file=pdf_path)

overrides = {}

for i, batch in enumerate(batches):
    print(f"Processing batch {i+1}/{len(batches)}...")
    prompt = f"""
I have provided the CommonApp Application Requirements PDF.
Based STRICTLY on this PDF, extract the testing and early admission policies for these specific colleges:
{json.dumps(batch, indent=2)}

IMPORTANT RULES for interpretation:
- If Test Policy is A (Always Required) or F (Test Flexible), use "Required". If it's N (Never Required), use "Optional". If not listed or NA, use null.
- For Early Decision (ED), True if there is an ED deadline.
- For Early Action (EA), True if there is an EA deadline.
- Make SURE you check both Regular Early Decision and Early Decision II logic in the PDF.
- If the college says REA or single-choice EA, set has_rea to True, has_ea to False, has_ed to False. (Only very elite schools use REA).
- Return dates as MM/DD (e.g. "11/01" or "11/03"). Use the first available early deadline. If no early deadline, set to null.
- Extract accurately from the 'Standardized Tests', 'ED Deadline', 'EA Deadline' columns.
- Ensure the keys exactly match my array entries.

Return exactly a JSON dictionary mapping the exact college name string to its object.
Return ONLY valid JSON output (no markdown format blocks like ```json, just raw JSON text).

Example Response:
{{
  "Princeton University": {{"test_policy": "Optional", "has_ed": false, "has_ea": false, "has_rea": true, "ed_deadline": null, "ea_deadline": null, "rea_deadline": "11/01"}},
  "Vanderbilt University": {{"test_policy": "Required", "has_ed": true, "has_ea": false, "has_rea": false, "ed_deadline": "11/01", "ea_deadline": null, "rea_deadline": null}}
}}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        data = json.loads(response.text)
        overrides.update(data)
    except Exception as e:
        print(f"Failed batch {i+1}: {e}")
        # Optional: Print raw text if fallback required
    time.sleep(3)

print("\nWriting overrides.json...")
with open("overrides.json", "w", encoding="utf-8") as f:
    json.dump(overrides, f, indent=4)

client.files.delete(name=uploaded_file.name)
print(f"Finished writing {len(overrides)} universities to overrides.json.")
