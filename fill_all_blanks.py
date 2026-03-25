import os
import json
import time
from google import genai
from google.genai import types
from generate import _load_or_fetch, _merge
from college_lists import NATIONAL_UNIVERSITIES, LIBERAL_ARTS_COLLEGES
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("No GEMINI_API_KEY found.")
    exit(1)
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

def build_missing_list():
    nat = _load_or_fetch(NATIONAL_UNIVERSITIES, "national_scorecard", "national_gemini", "National Universities", False)
    lac = _load_or_fetch(LIBERAL_ARTS_COLLEGES, "lac_scorecard", "lac_gemini", "Liberal Arts Colleges", False)
    
    missing_schools = []
    for r in nat + lac:
        mf = []
        if not r.get("_gpa_raw"): mf.append("avg_gpa_weighted")
        if not r.get("sat_act"): mf.append("sat_midpoint, act_composite")
        if not r.get("_test_policy_raw"): mf.append("test_policy")
        if not r.get("acceptance_rate"): mf.append("acceptance_rate_regular")
        if not get_due_disp(r): mf.append("has_ed, has_ea, has_rea, ed_deadline, ea_deadline, rea_deadline")
        if not r.get("_early_rate_raw"): mf.append("early_acceptance_rate")
        if not r.get("enrollment"): mf.append("total_enrollment")
        if not r.get("ratio"): mf.append("student_faculty_ratio")
        if not r.get("tuition"): mf.append("tuition_in_state, tuition_out_of_state")
        if not r.get("room_board"): mf.append("room_board")
        if not r.get("setting"): mf.append("setting")
        if r.get("defer") is None: mf.append("defer_policy")
        
        if mf:
            missing_schools.append({"name": r["name"], "missing": mf})
            
    return missing_schools

def main():
    print("Scanning for blank values in all 202 colleges...")
    missing_schools = build_missing_list()
    
    if not missing_schools:
        print("No missing data found!")
        return
        
    print(f"Found {len(missing_schools)} schools with blanks.")
    batch_size = 20
    batches = [missing_schools[i:i + batch_size] for i in range(0, len(missing_schools), batch_size)]
    
    new_overrides = {}

    for b_idx, batch in enumerate(batches):
        print(f"  [AI] Processing batch {b_idx+1}/{len(batches)} ({len(batch)} schools)...")
        prompt = (
            "You are an expert college admissions consultant. I have an exact list of colleges that have missing data in my database. "
            "Please provide the requested missing values based on the latest 2024-2025 admissions cycle.\n\n"
            "Output EXACTLY and ONLY a RAW JSON dictionary mapping the college name to another dictionary of keys.\n"
            "Here are the colleges and the exact data fields you MUST provide for each. "
            "IMPORTANT: ONLY provide the keys listed as missing!! Do not provide unrequested keys.\n"
            "If requested, format test_policy strictly as: \"Required\", \"Optional\", \"Blind\", or \"Test-Blind\".\n"
            "If requested, deadlines strictly as: \"MM/DD\".\n"
            "If requested, defer_policy as boolean.\n"
            "If requested, floats/ints normally.\n\n"
        )
        for m in batch:
            reqs = ", ".join(m['missing'])
            prompt += f"- {m['name']}: MUST provide -> {reqs}\n"
            
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            raw = resp.text
            idx1 = raw.find('{')
            idx2 = raw.rfind('}')
            if idx1 != -1 and idx2 != -1:
                parsed = json.loads(raw[idx1:idx2+1])
                for name, data in parsed.items():
                    new_overrides[name] = data
            else:
                print("    Failed to find JSON in response:", raw)
        except Exception as e:
            print(f"    Error on batch {b_idx+1}: {e}")
            
        time.sleep(2)
        
    # Read existing overrides
    overrides_path = "overrides.json"
    if os.path.exists(overrides_path):
        with open(overrides_path, "r", encoding="utf-8") as f:
            overrides = json.load(f)
    else:
        overrides = {}
        
    # Apply to overrides.json with asterisk
    for name, data in new_overrides.items():
        if name not in overrides:
            overrides[name] = {}
        
        # We append * to strings, and for floats/ints we convert them to strings with *
        for k, v in data.items():
            if v is None: continue
            
            # For booleans (like has_ed, defer_policy), do not append asterisk
            if isinstance(v, bool):
                overrides[name][k] = v
                continue
                
            if isinstance(v, str):
                overrides[name][k] = v.strip() + "*" if not v.endswith("*") else v
            elif isinstance(v, (int, float)):
                # If they passed an int/float, convert to str to add *
                overrides[name][k] = f"{v}*"
                
    with open(overrides_path, "w", encoding="utf-8") as f:
        json.dump(overrides, f, indent=4)
        
    print("Done! Overrides have been filled with AI estimated defaults (*).")

if __name__ == "__main__":
    main()
