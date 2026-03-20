# fetchers/scorecard.py
# Fetches official quantitative data from the US Dept. of Education College Scorecard API
# API docs: https://collegescorecard.ed.gov/data/documentation/

import os
import time
import requests

API_BASE = "https://api.data.gov/ed/collegescorecard/v1/schools"

FIELDS = ",".join([
    "school.name",
    "school.state",
    "school.locale",                                      # Setting (City/Suburb/Town/Rural)
    "latest.student.size",                                # Total Enrollment
    "latest.admissions.admission_rate.overall",           # Acceptance Rate (Regular)
    "latest.admissions.sat_scores.midpoint.critical_reading",
    "latest.admissions.sat_scores.midpoint.math",
    "latest.admissions.act_scores.midpoint.cumulative",
    "latest.cost.tuition.in_state",
    "latest.cost.tuition.out_of_state",
    "latest.cost.roomboard.oncampus",
    "latest.student.faculty_ratio",
])

LOCALE_MAP = {
    11: "City", 12: "City", 13: "City",
    21: "Suburban", 22: "Suburban", 23: "Suburban",
    31: "Town", 32: "Town", 33: "Town",
    41: "Rural", 42: "Rural", 43: "Rural",
}


def _search_school(name: str, state: str, api_key: str) -> dict | None:
    """Search for a single school by name and state. Returns raw API result."""
    params = {
        "api_key": api_key,
        "school.name": name,
        "school.state": state,
        "fields": FIELDS,
        "per_page": 1,
    }
    try:
        resp = requests.get(API_BASE, params=params, timeout=15)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None
    except Exception as e:
        print(f"  [Scorecard] Error fetching '{name}': {e}")
        return None


def _parse(raw: dict) -> dict:
    """Convert raw API response to a clean dict."""
    sat_read = raw.get("latest.admissions.sat_scores.midpoint.critical_reading")
    sat_math = raw.get("latest.admissions.sat_scores.midpoint.math")
    sat_total = (sat_read + sat_math) if (sat_read and sat_math) else None
    act = raw.get("latest.admissions.act_scores.midpoint.cumulative")

    tuition_in  = raw.get("latest.cost.tuition.in_state")
    tuition_out = raw.get("latest.cost.tuition.out_of_state")
    room_board  = raw.get("latest.cost.roomboard.oncampus")

    # Total tuition = out-of-state tuition + room & board (most relevant for elite schools)
    total_tuition = None
    if tuition_out and room_board:
        total_tuition = tuition_out + room_board

    locale_code = raw.get("school.locale")
    setting = LOCALE_MAP.get(locale_code, "N/A") if locale_code else "N/A"

    acc_rate = raw.get("latest.admissions.admission_rate.overall")

    return {
        "enrollment":       raw.get("latest.student.size"),
        "acceptance_rate":  round(acc_rate * 100, 1) if acc_rate else None,  # as %
        "sat_total":        int(sat_total) if sat_total else None,
        "act_midpoint":     int(act) if act else None,
        "tuition_in":       tuition_in,
        "tuition_out":      tuition_out,
        "room_board":       room_board,
        "total_tuition":    total_tuition,
        "faculty_ratio":    raw.get("latest.student.faculty_ratio"),
        "setting":          setting,
        "scorecard_name":   raw.get("school.name"),
    }


def fetch_scorecard_data(colleges: list[dict], api_key: str) -> dict:
    """
    Fetch College Scorecard data for a list of colleges.
    colleges: list of {"name": ..., "state": ...}
    Returns: {"CollegeName": {parsed fields}, ...}
    """
    results = {}
    total = len(colleges)
    for i, college in enumerate(colleges, 1):
        name  = college["name"]
        state = college["state"]
        print(f"  [Scorecard] ({i}/{total}) Fetching: {name}")
        raw = _search_school(name, state, api_key)
        if raw:
            results[name] = _parse(raw)
        else:
            results[name] = {}
        time.sleep(0.3)  # gentle rate limiting
    return results
