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
client = genai.Client(api_key=api_key)

def get_due_disp(r):
    due_raw = r.get("_due_date_raw")
    if due_raw: return due_raw
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
        if not r.get("sat_act"): mf.append("sat_act_override (a string e.g. 'SAT 1310-1530' or 'Test-Blind' or 'N/A')")
        if not get_due_disp(r): mf.append("due_date_override (a string e.g. 'UC: 11/30' or '11/01' or 'N/A')")
        
        # for early acceptance rate, check if it's evaluated as blank/N/A
        er = str(r.get("_early_rate_raw"))
        if not r.get("_early_rate_raw") or er == "0.0" or er == "0.0%" or er.startswith("0.0"):
            mf.append("early_acceptance_rate (a string like '10.5%' or 'N/A')")
        
        if mf:
            missing_schools.append({"name": r["name"], "missing": mf})
            
    return missing_schools

def main():
    print("Scanning for stubborn blanks (SAT/ACT, Due Date, Zero Early Rates) in all 202 colleges...")
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
            "You are an expert college admissions consultant. I have a list of colleges that have missing data in my database. "
            "Because these are edge cases (like UC schools being Test-Blind and having no Early Action but a strict regular deadline), I need YOU to supply specific STRING FALLBACKS for them.\n\n"
            "Output EXACTLY and ONLY a RAW JSON dictionary mapping the college name to another dictionary of keys.\n"
            "For each college, provide EXACTLY the keys requested.\n"
            "IMPORTANT NOTES:\n"
            "- If requested 'sat_act_override': return a string like 'SAT 1300-1530' (historical typical range if test-blind), or 'Test-Blind', or 'N/A'.\n"
            "- If requested 'due_date_override': return a string like 'UC: 11/30' or 'N/A' or appropriate phrasing so the column isn't empty.\n"
            "- If requested 'early_acceptance_rate': return a string like '12.5%' or 'N/A'.\n\n"
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
        
    overrides_path = "overrides.json"
    if os.path.exists(overrides_path):
        with open(overrides_path, "r", encoding="utf-8") as f:
            overrides = json.load(f)
    else:
        overrides = {}
        
    # Merge
    for name, data in new_overrides.items():
        if name not in overrides:
            overrides[name] = {}
        for k, v in data.items():
            if v is not None:
                # Append an asterisk if it's a string from this batch
                val_str = str(v).strip()
                if not val_str.endswith("*"): val_str += " *"
                overrides[name][k] = val_str
                
    with open(overrides_path, "w", encoding="utf-8") as f:
        json.dump(overrides, f, indent=4)
        
    print("Done! Overrides have been forced locally.")

if __name__ == "__main__":
    main()
