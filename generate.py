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

load_dotenv()

SCORECARD_API_KEY = os.getenv("SCORECARD_API_KEY", "")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")

OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")


# ── Data assembly ────────────────────────────────────────────────────────────

def _merge(college: dict, scorecard: dict, gemini: dict) -> dict:
    name  = college["name"]
    state = college["state"]
    sc    = scorecard.get(name, {})
    gm    = gemini.get(name, {})

    # SAT/ACT — Gemini primary (more accurate for elite schools), Scorecard fallback
    gm_sat = gm.get("sat_midpoint")
    gm_act = gm.get("act_composite")
    sc_sat = sc.get("sat_total")
    sc_act = sc.get("act_midpoint")
    sat = gm_sat or sc_sat
    act = gm_act or sc_act
    sat_act_ai = bool(gm_sat or gm_act)
    parts = []
    if sat: parts.append(f"SAT {sat}")
    if act: parts.append(f"ACT {act}")
    sat_act = " / ".join(parts) if parts else None

    # Tuition — Gemini primary (Scorecard often wrong/null for elite schools), Scorecard fallback
    gm_t_in  = gm.get("tuition_in_state")
    gm_t_out = gm.get("tuition_out_of_state")
    gm_rb    = gm.get("room_board")
    sc_t_in  = sc.get("tuition_in")
    sc_t_out = sc.get("tuition_out")
    sc_rb    = sc.get("room_board")

    t_in  = gm_t_in  if gm_t_in  is not None else sc_t_in
    t_out = gm_t_out if gm_t_out is not None else sc_t_out
    rb    = gm_rb    if gm_rb    is not None else sc_rb
    tuition_ai = gm_t_in is not None or gm_t_out is not None

    tuition = None
    if t_in and t_out:
        tuition = f"${t_in:,} / ${t_out:,}" if t_in != t_out else f"${t_out:,}"
    elif t_out:
        tuition = f"${t_out:,}"
    elif t_in:
        tuition = f"${t_in:,}"

    total = (t_out + rb) if (t_out and rb) else sc.get("total_tuition")

    # Enrollment — Gemini primary (Scorecard often wrong for elite schools), Scorecard fallback
    gm_enroll = gm.get("total_enrollment")
    sc_enroll  = sc.get("enrollment")
    enroll = gm_enroll if gm_enroll is not None else sc_enroll
    enroll_ai = gm_enroll is not None

    # Student:Faculty ratio — Gemini primary, Scorecard fallback
    gm_ratio = gm.get("student_faculty_ratio")
    sc_ratio  = sc.get("faculty_ratio")
    ratio = gm_ratio if gm_ratio is not None else sc_ratio
    ratio_ai = gm_ratio is not None

    # Acceptance rate — Gemini primary (Scorecard often wrong/missing for elite schools)
    gm_acc = gm.get("acceptance_rate_regular")
    sc_acc = sc.get("acceptance_rate")
    acc = gm_acc if gm_acc is not None else sc_acc
    acc_ai = gm_acc is not None

    defer_raw = gm.get("defer_policy")

    return {
        "name":             name,
        "state":            state,
        "_rank_raw":        gm.get("us_news_rank"),
        "_gpa_raw":         gm.get("avg_gpa_weighted"),
        "_test_policy_raw": gm.get("test_policy"),
        "_has_ed":          bool(gm.get("has_ed")),
        "_has_ea":          bool(gm.get("has_ea")),
        "_ed_deadline":     gm.get("ed_deadline"),
        "_ea_deadline":     gm.get("ea_deadline"),
        "_early_rate_raw":  gm.get("early_acceptance_rate"),
        "sat_act":          sat_act,
        "_sat_act_ai":      sat_act_ai,
        "acceptance_rate":  f"{acc}%" if acc is not None else None,
        "_acc_ai":          acc_ai,
        "enrollment":       f"{enroll:,}" if enroll else None,
        "_enrollment_ai":   enroll_ai,
        "ratio":            f"{ratio}:1" if ratio else None,
        "_ratio_ai":        ratio_ai,
        "tuition":          tuition,
        "_tuition_ai":      tuition_ai,
        "room_board":       f"${rb:,}" if rb else None,
        "total_tuition":    f"${total:,}" if total else None,
        "setting":          {"City": "Urban", "Town": "Rural"}.get(sc.get("setting"), sc.get("setting")),
        "defer":            "Yes" if defer_raw is True else ("No" if defer_raw is False else None),
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
