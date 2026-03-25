# fetchers/gemini_fetcher.py
# Uses Google Gemini API to fetch policy/qualitative data for each college.
# All values returned are marked as AI-estimated.

import json
import time
import re
from google import genai
from google.genai import types

BATCH_SIZE = 15  # colleges per Gemini request (balance speed vs. accuracy)

SYSTEM_PROMPT = """You are a precise college admissions data assistant.
Return ONLY valid JSON with no markdown, no explanation, no code fences.
Use null for any field you are not confident about — EXCEPT avg_gpa_weighted, sat_midpoint, act_composite, acceptance_rate_regular, early_acceptance_rate, total_enrollment, student_faculty_ratio, tuition_in_state, tuition_out_of_state, and room_board:
for these ten fields always provide your best estimate based on publicly known data. Never return null for them.
For early_acceptance_rate: if the school has no early program (has_ed=false AND has_ea=false), return 0. Otherwise always estimate.
Base your answers on the most recent publicly available data (2024-2025 academic year)."""

def _build_prompt(colleges: list[dict], category: str) -> str:
    names = [f'{i+1}. {c["name"]} ({c["state"]})' for i, c in enumerate(colleges)]
    school_list = "\n".join(names)

    return f"""For the following {category}, provide the most recent (2024-2025) admissions data.

Schools:
{school_list}

Return a JSON array. Each object must have EXACTLY these fields:
- "name": exact school name from the list above
- "us_news_rank": integer US News {category} rank, or null
- "avg_gpa_weighted": float, average weighted GPA of admitted freshmen class. Use widely published figures (e.g. Harvard ~4.18, MIT ~4.17, Stanford ~4.18). Always provide your best estimate — do NOT return null.
- "sat_midpoint": integer, SAT composite midpoint score of admitted freshmen (e.g. 1510). Use widely known figures. Always provide your best estimate — do NOT return null.
- "act_composite": integer, ACT composite midpoint score of admitted freshmen (e.g. 34). Use widely known figures. Always provide your best estimate — do NOT return null.
- "acceptance_rate_regular": float as percentage, overall (Regular Decision) acceptance rate (e.g. 3.5 means 3.5%). Use the most recent published figures. Always provide your best estimate — do NOT return null.
- "test_policy": one of "Required", "Optional", "Blind", or null
- "has_ed": true or false — does the school offer Early Decision (binding)?
- "has_ea": true or false — does the school offer NON-restrictive Early Action (applicants may simultaneously apply ED/REA elsewhere)? Examples: MIT, UMich, UVA, UChicago (also has ED).
- "has_rea": true or false — does the school offer Restrictive Early Action / Single-Choice Early Action (non-binding but applicants generally cannot apply ED or REA to other private schools simultaneously)? Examples: Harvard (SCEA), Princeton (REA), Yale (REA), Stanford (REA), Notre Dame (REA). IMPORTANT: has_rea=true means has_ed and has_ea should both be false.
- "ed_deadline": string "MM/DD" format (e.g. "11/01"), or null
- "ea_deadline": string "MM/DD" format (e.g. "11/01"), or null
- "rea_deadline": string "MM/DD" format for Restrictive Early Action deadline (e.g. "11/01"), or null
- "early_acceptance_rate": float as percentage for ED/EA/REA acceptance rate (e.g. 18.5 means 18.5%). Always provide your best estimate. Use 0 only if no early program exists.
- "defer_policy": true if the school defers early applicants to RD, false if not, null if unknown
- "total_enrollment": integer, total undergraduate enrollment (e.g. Harvard ~7100, MIT ~4600, Stanford ~7800, UPenn ~10000, Caltech ~938). Always provide your best estimate — do NOT return null.
- "student_faculty_ratio": integer, student-to-faculty ratio as students per faculty member (e.g. 6 means 6:1). Always provide your best estimate — do NOT return null.
- "tuition_in_state": integer, annual in-state undergraduate tuition in USD for 2024-2025 (e.g. UCLA 14312, Michigan 17736). For private schools same as out-of-state tuition. Always provide your best estimate — do NOT return null.
- "tuition_out_of_state": integer, annual out-of-state undergraduate tuition in USD for 2024-2025 (e.g. UCLA 44066, Michigan 60946). For private schools same as in-state (e.g. Harvard 61676, MIT 62396, UChicago 65440, Caltech 63225). Always provide your best estimate — do NOT return null.
- "room_board": integer, typical annual on-campus room and board cost in USD for 2024-2025 (e.g. Harvard 21190, MIT 20280, Stanford 21315). Always provide your best estimate — do NOT return null.

Return ONLY the JSON array, nothing else."""


def _extract_json(text: str) -> list:
    """Robustly extract a JSON array from Gemini's response."""
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?", "", text).strip()
    # Find the first [ ... ] block
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def fetch_gemini_data(colleges: list[dict], api_key: str, category: str) -> dict:
    """
    Fetch AI-estimated policy/qualitative data for all colleges via Gemini.
    category: "National Universities" or "Liberal Arts Colleges"
    Returns: {"CollegeName": {gemini fields}, ...}
    """
    client = genai.Client(api_key=api_key)

    results = {}
    batches = [colleges[i:i+BATCH_SIZE] for i in range(0, len(colleges), BATCH_SIZE)]
    total_batches = len(batches)

    for batch_num, batch in enumerate(batches, 1):
        print(f"  [Gemini] Batch {batch_num}/{total_batches} ({len(batch)} schools) ...")
        prompt = _build_prompt(batch, category)

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                ),
            )
            raw_text = response.text
            parsed = _extract_json(raw_text)

            for entry in parsed:
                name = entry.get("name")
                if not name:
                    continue
                # Match against original college name (flexible)
                matched_name = _find_match(name, batch)
                if matched_name:
                    results[matched_name] = {
                        "us_news_rank":           entry.get("us_news_rank"),
                        "avg_gpa_weighted":       entry.get("avg_gpa_weighted"),
                        "sat_midpoint":           entry.get("sat_midpoint"),
                        "act_composite":          entry.get("act_composite"),
                        "acceptance_rate_regular": entry.get("acceptance_rate_regular"),
                        "test_policy":            entry.get("test_policy"),
                        "has_ed":              entry.get("has_ed"),
                        "has_ea":              entry.get("has_ea"),
                        "has_rea":             entry.get("has_rea"),
                        "ed_deadline":         entry.get("ed_deadline"),
                        "ea_deadline":         entry.get("ea_deadline"),
                        "rea_deadline":        entry.get("rea_deadline"),
                        "early_acceptance_rate": entry.get("early_acceptance_rate"),
                        "defer_policy":        entry.get("defer_policy"),
                        "total_enrollment":    entry.get("total_enrollment"),
                        "student_faculty_ratio": entry.get("student_faculty_ratio"),
                        "tuition_in_state":    entry.get("tuition_in_state"),
                        "tuition_out_of_state": entry.get("tuition_out_of_state"),
                        "room_board":          entry.get("room_board"),
                    }

        except Exception as e:
            print(f"  [Gemini] Error on batch {batch_num}: {e}")
            # Fill with nulls for failed batch
            for c in batch:
                results[c["name"]] = {k: None for k in [
                    "us_news_rank", "avg_gpa_weighted", "sat_midpoint", "act_composite",
                    "acceptance_rate_regular", "test_policy",
                    "has_ed", "has_ea", "has_rea", "ed_deadline", "ea_deadline", "rea_deadline",
                    "early_acceptance_rate", "defer_policy",
                    "total_enrollment", "student_faculty_ratio",
                    "tuition_in_state", "tuition_out_of_state", "room_board",
                ]}

        if batch_num < total_batches:
            time.sleep(2)  # avoid rate limiting between batches

    return results


def _find_match(gemini_name: str, batch: list[dict]) -> str | None:
    """Find the best-matching college name from the batch."""
    gemini_lower = gemini_name.lower().strip()
    # Exact match first
    for c in batch:
        if c["name"].lower().strip() == gemini_lower:
            return c["name"]
    # Partial match
    for c in batch:
        if gemini_lower in c["name"].lower() or c["name"].lower() in gemini_lower:
            return c["name"]
    return None
