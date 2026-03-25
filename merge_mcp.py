import json
import re
import os

overrides = {}
if os.path.exists('overrides.json'):
    try:
        overrides = json.load(open("overrides.json", "r", encoding="utf-8"))
    except:
        pass

files = [
    r"C:\Users\andye\.gemini\antigravity\brain\1c8f5240-a4f7-4ea0-bd83-1c7209225198\.system_generated\steps\269\output.txt",
    r"C:\Users\andye\.gemini\antigravity\brain\1c8f5240-a4f7-4ea0-bd83-1c7209225198\.system_generated\steps\288\output.txt",
    r"C:\Users\andye\.gemini\antigravity\brain\1c8f5240-a4f7-4ea0-bd83-1c7209225198\.system_generated\steps\289\output.txt",
    r"C:\Users\andye\.gemini\antigravity\brain\1c8f5240-a4f7-4ea0-bd83-1c7209225198\.system_generated\steps\290\output.txt"
]

for f in files:
    if os.path.exists(f):
        content = open(f, "r", encoding="utf-8").read()
        try:
            data = json.loads(content)
            ans = data.get("data", {}).get("answer", "")
            idx1 = ans.find('{')
            idx2 = ans.rfind('}')
            if idx1 != -1 and idx2 != -1:
                json_str = ans[idx1:idx2+1]
                parsed = json.loads(json_str)
                overrides.update(parsed)
        except Exception as e:
            print(f"Error parsing {f}: {e}")

overrides.update({
    "Muskingum University": {"test_policy": "Optional", "has_ed": False, "has_ea": False, "has_rea": False, "ed_deadline": None, "ea_deadline": None, "rea_deadline": None},
    "Albion College": {"test_policy": "Optional", "has_ed": False, "has_ea": True, "has_rea": False, "ed_deadline": None, "ea_deadline": "11/01", "rea_deadline": None}
})

with open("overrides.json", "w", encoding="utf-8") as out:
    json.dump(overrides, out, indent=4)
print(f"Total overrides loaded: {len(overrides)}")
