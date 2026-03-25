import glob
import json
import re
import os

overrides = {}
if os.path.exists("overrides.json"):
    try:
        overrides = json.load(open("overrides.json", "r", encoding="utf-8"))
    except:
        pass

files = glob.glob(r"C:\Users\andye\.gemini\antigravity\brain\1c8f5240-a4f7-4ea0-bd83-1c7209225198\.system_generated\steps\*\output.txt")

for f in files:
    try:
        content = open(f, "r", encoding="utf-8").read()
        try:
            data = json.loads(content)
            ans = data.get("data", {}).get("answer", "")
            idx1 = ans.find('{')
            idx2 = ans.rfind('}')
            if idx1 != -1 and idx2 != -1:
                json_str = ans[idx1:idx2+1]
                parsed = json.loads(json_str)
                for k, v in parsed.items():
                    if isinstance(v, dict) and "test_policy" in v:
                        overrides[k] = v
        except Exception:
            pass
    except Exception as e:
        print(f"Error reading {f}: {e}")

overrides.update({
    "Muskingum University": {"test_policy": "Optional", "has_ed": False, "has_ea": False, "has_rea": False, "ed_deadline": None, "ea_deadline": None, "rea_deadline": None},
    "Albion College": {"test_policy": "Optional", "has_ed": False, "has_ea": True, "has_rea": False, "ed_deadline": None, "ea_deadline": "11/01", "rea_deadline": None}
})

with open("overrides.json", "w", encoding="utf-8") as out:
    json.dump(overrides, out, indent=4)
print(f"Total overrides loaded: {len(overrides)}")
