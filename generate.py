#!/usr/bin/env python3
"""
generate.py — Elite U.S. College Data Sheet
============================================
Run this script to fetch college data and generate output/index.html.
Then manually upload output/index.html to Hostinger File Manager.

Usage:
  python generate.py              # use cache if fresh (<365 days)
  python generate.py --refresh    # force re-fetch all data
"""

import os
import argparse
from dotenv import load_dotenv

from college_lists import NATIONAL_UNIVERSITIES, LIBERAL_ARTS_COLLEGES
from cache_manager import load_cache, save_cache, clear_cache, cache_age, cache_days_remaining
from fetchers.scorecard import fetch_scorecard_data
from fetchers.gemini_fetcher import fetch_gemini_data
from html_builder import build_html
import json

overrides = {}
overrides_path = os.path.join(os.path.dirname(__file__), "overrides.json")
if os.path.exists(overrides_path):
    with open(overrides_path, "r", encoding="utf-8") as f:
        overrides = json.load(f)


load_dotenv()

SCORECARD_API_KEY = os.getenv("SCORECARD_API_KEY", "")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")

OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")


# ── Data assembly ────────────────────────────────────────────────────────────

def fmt_int(val):
    if val is None: return None
    if isinstance(val, str): return val
    return f"{val:,}"

def fmt_money(val):
    if val is None: return None
    if isinstance(val, str): return f"${val}" if not val.startswith("$") else val
    return f"${val:,}"

def _merge(college: dict, scorecard: dict, gemini: dict) -> dict:
    name  = college["name"]
    state = college["state"]
    sc    = scorecard.get(name, {})
    gm    = gemini.get(name, {})
    ov    = overrides.get(name, {})

    def _v(key):
        return ov.get(key, gm.get(key))

    # SAT/ACT
    gm_sat = _v("sat_midpoint")
    gm_act = _v("act_composite")
    sc_sat = sc.get("sat_total")
    sc_act = sc.get("act_midpoint")
    sat = gm_sat if gm_sat is not None else sc_sat
    act = gm_act if gm_act is not None else sc_act
    sat_act_ai = bool(gm_sat or gm_act) or bool(ov.get("sat_act_override"))
    
    sat_act_ov = ov.get("sat_act_override")
    if sat_act_ov:
        sat_act = sat_act_ov
    else:
        parts = []
        if sat: parts.append(f"SAT {sat}")
        if act: parts.append(f"ACT {act}")
        sat_act = " / ".join(parts) if parts else None

    # Tuition
    gm_t_in  = _v("tuition_in_state")
    gm_t_out = _v("tuition_out_of_state")
    gm_rb    = _v("room_board")
    sc_t_in  = sc.get("tuition_in")
    sc_t_out = sc.get("tuition_out")
    sc_rb    = sc.get("room_board")

    t_in  = gm_t_in  if gm_t_in  is not None else sc_t_in
    t_out = gm_t_out if gm_t_out is not None else sc_t_out
    rb    = gm_rb    if gm_rb    is not None else sc_rb
    tuition_ai = gm_t_in is not None or gm_t_out is not None

    tuition = None
    if t_in and t_out:
        tuition = f"{fmt_money(t_in)} / {fmt_money(t_out)}" if t_in != t_out else fmt_money(t_out)
    elif t_out:
        tuition = fmt_money(t_out)
    elif t_in:
        tuition = fmt_money(t_in)

    total = None
    if isinstance(t_out, str) and "*" in t_out: total = None
    elif isinstance(rb, str) and "*" in rb: total = None
    elif t_out and rb: total = t_out + rb
    else: total = sc.get("total_tuition")
    if _v("total_tuition"): total = _v("total_tuition")

    # Enrollment
    gm_enroll = _v("total_enrollment")
    sc_enroll  = sc.get("enrollment")
    enroll = gm_enroll if gm_enroll is not None else sc_enroll
    enroll_ai = gm_enroll is not None

    # Student:Faculty
    gm_ratio = _v("student_faculty_ratio")
    sc_ratio  = sc.get("faculty_ratio")
    ratio = gm_ratio if gm_ratio is not None else sc_ratio
    ratio_ai = gm_ratio is not None

    # Acceptance rate
    gm_acc = _v("acceptance_rate_regular")
    sc_acc = sc.get("acceptance_rate")
    acc = gm_acc if gm_acc is not None else sc_acc
    acc_ai = gm_acc is not None

    defer_raw = _v("defer_policy")
    
    acc_str = None
    if acc is not None:
        if isinstance(acc, str): acc_str = acc if "%" in acc else f"{acc}%"
        else: acc_str = f"{acc}%"

    ratio_str = None
    if ratio is not None:
        if isinstance(ratio, str): ratio_str = ratio
        else: ratio_str = f"{ratio}:1"

    defer_str = None
    if isinstance(defer_raw, str): defer_str = defer_raw
    else: defer_str = "Yes" if defer_raw is True else ("No" if defer_raw is False else None)

    return {
        "name":             name,
        "state":            state,
        "_rank_raw":        _v("us_news_rank"),
        "_gpa_raw":         _v("avg_gpa_weighted"),
        "_test_policy_raw": ov.get("test_policy", college.get("test_policy") or gm.get("test_policy")),
        "_has_ed":          ov.get("has_ed",     college.get("has_ed")     if "has_ed"     in college else bool(gm.get("has_ed"))),
        "_has_ea":          ov.get("has_ea",     college.get("has_ea")     if "has_ea"     in college else bool(gm.get("has_ea"))),
        "_has_rea":         ov.get("has_rea",    college.get("has_rea")    if "has_rea"    in college else bool(gm.get("has_rea"))),
        "_ed_deadline":     ov.get("ed_deadline", college.get("ed_deadline") or gm.get("ed_deadline")),
        "_ea_deadline":     ov.get("ea_deadline", college.get("ea_deadline") or gm.get("ea_deadline")),
        "_rea_deadline":    ov.get("rea_deadline", college.get("rea_deadline") or gm.get("rea_deadline")),
        "_due_date_raw":    ov.get("due_date_override"),
        "_early_rate_raw":  _v("early_acceptance_rate"),
        "sat_act":          sat_act,
        "_sat_act_ai":      sat_act_ai,
        "acceptance_rate":  acc_str,
        "_acc_ai":          acc_ai,
        "enrollment":       fmt_int(enroll),
        "_enrollment_ai":   enroll_ai,
        "ratio":            ratio_str,
        "_ratio_ai":        ratio_ai,
        "tuition":          tuition,
        "_tuition_ai":      tuition_ai,
        "room_board":       fmt_money(rb),
        "total_tuition":    fmt_money(total),
        "setting":          {"City": "Urban", "Town": "Rural"}.get(sc.get("setting"), sc.get("setting")),
        "defer":            defer_str,
    }


def _load_or_fetch(colleges, sc_key, gm_key, category, force_refresh=False):
    if force_refresh:
        clear_cache(sc_key)
        clear_cache(gm_key)

    # Scorecard
    sc_cache = load_cache(sc_key)
    if sc_cache:
        print(f"  [Cache] Scorecard: {cache_age(sc_key)}")
        sc_data = sc_cache["data"]
    else:
        print(f"  [Fetch] College Scorecard API ({len(colleges)} schools) ...")
        sc_data = fetch_scorecard_data(colleges, SCORECARD_API_KEY) if SCORECARD_API_KEY else {}
        if not SCORECARD_API_KEY:
            print("  ⚠  SCORECARD_API_KEY not set — skipping")
        save_cache(sc_key, {"data": sc_data})

    # Gemini
    gm_cache = load_cache(gm_key)
    if gm_cache:
        print(f"  [Cache] Gemini: {cache_age(gm_key)}")
        gm_data = gm_cache["data"]
    else:
        print(f"  [Fetch] Gemini AI data ...")
        gm_data = fetch_gemini_data(colleges, GEMINI_API_KEY, category) if GEMINI_API_KEY else {}
        if not GEMINI_API_KEY:
            print("  ⚠  GEMINI_API_KEY not set — skipping")
        save_cache(gm_key, {"data": gm_data})

    rows = [_merge(c, sc_data, gm_data) for c in colleges]
    rows.sort(key=lambda r: (r["_rank_raw"] is None, r["_rank_raw"] or 9999))
    return rows


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Elite U.S. College Data Sheet Generator")
    parser.add_argument("--refresh", action="store_true", help="Force re-fetch (ignore cache)")
    args = parser.parse_args()

    print("=" * 60)
    print("  Elite U.S. College Data Sheet — Generator")
    print("=" * 60)

    if args.refresh:
        print("[Info] --refresh: clearing all caches\n")

    print("\n📚 National Universities ...")
    nat_rows = _load_or_fetch(
        NATIONAL_UNIVERSITIES,
        "national_scorecard", "national_gemini",
        "National Universities",
        force_refresh=args.refresh,
    )

    print("\n🌿 Liberal Arts Colleges ...")
    lac_rows = _load_or_fetch(
        LIBERAL_ARTS_COLLEGES,
        "lac_scorecard", "lac_gemini",
        "Liberal Arts Colleges",
        force_refresh=args.refresh,
    )

    print("\n🔨 Generating HTML ...")
    all_remaining = [
        cache_days_remaining("national_scorecard"),
        cache_days_remaining("national_gemini"),
        cache_days_remaining("lac_scorecard"),
        cache_days_remaining("lac_gemini"),
    ]
    valid = [d for d in all_remaining if d is not None]
    days_until_refresh = min(valid) if valid else 0

    html = build_html(
        nat_rows, lac_rows,
        cache_age("national_scorecard"),
        cache_age("national_gemini"),
        days_until_refresh,
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n✅ 완료!")
    print(f"   생성된 파일: {OUTPUT_FILE}")
    print(f"   National Universities: {len(nat_rows)}개")
    print(f"   Liberal Arts Colleges: {len(lac_rows)}개")
    print()
    print("─" * 60)
    print("📤 Hostinger 업로드 방법:")
    print("   1. hPanel → File Manager → public_html 이동")
    print("   2. 'college-data' 폴더 생성")
    print("   3. output/index.html 파일 업로드")
    print("   4. https://elite4usa.com/college-data/ 접속 확인")
    print("─" * 60)


if __name__ == "__main__":
    main()
