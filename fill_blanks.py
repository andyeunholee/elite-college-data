import os
import json
from google import genai
from google.genai import types
from generate import _load_or_fetch, _merge
from college_lists import NATIONAL_UNIVERSITIES, LIBERAL_ARTS_COLLEGES
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

def get_due_disp(r):
    has_ed  = r.get("_has_ed",  False)
    has_ea  = r.get("_has_ea",  False)
    has_rea = r.get("_has_rea", False)
    ed_dl  = r.get("_ed_deadline")
    ea_dl  = r.get("_ea_deadline")
    rea_dl = r.get("_rea_deadline")
    due_parts = []
    if has_rea and rea_dl: due_parts.append(f"REA: {rea_dl}")
    if has_ed and ed_dl: due_parts.append(f"ED: {ed_dl}")
    if has_ea and ea_dl: due_parts.append(f"EA: {ea_dl}")
    return " / ".join(due_parts) if due_parts else None

def main():
    print("Loading data...")
    nat = _load_or_fetch(NATIONAL_UNIVERSITIES, "national_scorecard", "national_gemini", "National Universities", False)
    lac = _load_or_fetch(LIBERAL_ARTS_COLLEGES, "lac_scorecard", "lac_gemini", "Liberal Arts Colleges", False)
    
    missing_schools = []
    for r in nat + lac:
        missing_fields = []
        if not r["_test_policy_raw"]: missing_fields.append("test_policy")
        if not get_due_disp(r): missing_fields.append("due_date (need has_ed, has_ea, ed_deadline etc.)")
        if not r["_early_rate_raw"]: missing_fields.append("early_acceptance_rate")
        
        if missing_fields:
            missing_schools.append({"name": r["name"], "missing": missing_fields})
            
    if not missing_schools:
        print("No missing data found!")
        return
        
    print(f"Found {len(missing_schools)} schools with missing info. Querying Gemini 2.5 Flash...")
    
    prompt = (
        "You are an expert college admissions consultant. I have an exact list of colleges that have missing data in my database. "
        "Please provide the requested missing values based on the latest 2024-2025 admissions cycle.\n\n"
        "Output EXACTLY and ONLY a RAW JSON dictionary mapping the college name to another dictionary of keys.\n"
        "Required keys for EVERY college listed below:\n"
        '- "test_policy" (strictly one of: "Required", "Optional", "Blind", "Test-Blind", or null)\n'
        '- "has_ed" (bool)\n'
        '- "has_ea" (bool)\n'
        '- "has_rea" (bool)\n'
        '- "ed_deadline" (string "MM/DD" or null)\n'
        '- "ea_deadline" (string "MM/DD" or null)\n'
        '- "rea_deadline" (string "MM/DD" or null)\n'
        '- "early_acceptance_rate" (float like 15.5 or null)\n\n'
        "Here are the colleges and the fields they specifically need. Make sure to provide ALL 8 keys for each college regardless, but focus on getting these right:\n"
    )
    for m in missing_schools:
        prompt += f"- {m['name']}: missing {', '.join(m['missing'])}\n"
        
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    raw = resp.text
    
    idx1 = raw.find('{')
    idx2 = raw.rfind('}')
    json_str = raw[idx1:idx2+1]
    
    try:
        new_data = json.loads(json_str)
    except Exception as e:
        print("Failed to parse Gemini response:", e)
        print(raw)
        return
        
    # Load overrides
    overrides_path = "overrides.json"
    if os.path.exists(overrides_path):
        with open(overrides_path, "r", encoding="utf-8") as f:
            overrides = json.load(f)
    else:
        overrides = {}
        
    # Merge and append *
    for name, data in new_data.items():
        if name not in overrides:
            overrides[name] = {}
            
        if data.get("test_policy"):
            overrides[name]["test_policy"] = data["test_policy"] + "*"
            
        for k in ["has_ed", "has_ea", "has_rea"]:
            if k in data and data[k] is not None:
                overrides[name][k] = data[k]
                
        for k in ["ed_deadline", "ea_deadline", "rea_deadline"]:
            if data.get(k):
                overrides[name][k] = data[k] + "*"
                
        if data.get("early_acceptance_rate"):
            # store it as a string with * so the html_builder formats it
            val = data["early_acceptance_rate"]
            try:
                overrides[name]["early_acceptance_rate"] = f"{float(val):.1f}% *"
            except:
                overrides[name]["early_acceptance_rate"] = f"{val} *"
            
    with open(overrides_path, "w", encoding="utf-8") as f:
        json.dump(overrides, f, indent=4)
        
    print("Done! Overrides have been filled with AI estimated defaults (*).")

if __name__ == "__main__":
    main()
