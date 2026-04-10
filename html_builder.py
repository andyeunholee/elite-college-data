# html_builder.py
# Converts merged college data into a complete static HTML page.

import json
import os
from datetime import datetime

# ── Blog URL mapping ───────────────────────────────────────────────────────
_BLOG_URLS: dict[str, str] = {}
_blog_path = os.path.join(os.path.dirname(__file__), "blog_urls.json")
if os.path.exists(_blog_path):
    with open(_blog_path, "r", encoding="utf-8") as f:
        _BLOG_URLS = json.load(f)

# ── CSS + colour constants ──────────────────────────────────────────────────
_CSS = """
:root {
  --primary: #1a3a6b;
  --accent:  #c8a951;
  --ai-bg:   #fff8e1;
  --ai-brd:  #f0c040;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Inter', -apple-system, sans-serif;
  background: #f4f6f9;
  color: #222;
}

/* ── Header ── */
.site-header {
  background: linear-gradient(135deg, #1a3a6b 0%, #0d2240 100%);
  color: #fff;
  padding: 1.8rem 2rem 1.2rem;
  border-bottom: 4px solid #c8a951;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}
.site-header h1  { font-size: 1.7rem; font-weight: 700; }
.site-header sub { font-size: .85rem; opacity: .7; margin-top: .2rem; display:block; }
.updated         { font-size: .78rem; opacity: .7; text-align: right; }
.header-btn {
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.4);
  color: #fff;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: .75rem;
  cursor: pointer;
  margin-top: 8px;
  transition: background .2s;
}
.header-btn:hover { background: rgba(255,255,255,0.28); }

/* ── Info bar ── */
.info-bar {
  background: #fff;
  border-bottom: 1px solid #dee2e6;
  padding: .5rem 2rem;
  font-size: .78rem;
  color: #555;
  display: flex;
  gap: 1.8rem;
  align-items: center;
}
.ai-badge {
  background: #fff8e1;
  border: 1px solid #f0c040;
  border-radius: 4px;
  padding: 1px 6px;
  font-size: .7rem;
  font-weight: 700;
  color: #7a5e00;
}

/* ── Tabs ── */
.tabs { display:flex; gap:4px; padding: 1rem 2rem 0; }
.tab-btn {
  padding: .55rem 1.4rem;
  border: 2px solid #1a3a6b;
  border-bottom: none;
  background: #fff;
  color: #1a3a6b;
  font-weight: 700;
  font-size: .88rem;
  cursor: pointer;
  border-radius: 8px 8px 0 0;
}
.tab-btn.active { background: #1a3a6b; color: #fff; }

/* ── Table wrapper ── */
.tab-panel { display: none; }
.tab-panel.active { display: block; }
.table-wrap {
  background: #fff;
  margin: 0 2rem 2rem;
  border-radius: 0 0 10px 10px;
  box-shadow: 0 2px 14px rgba(0,0,0,.07);
  padding: 1rem 1rem 1.4rem;
  overflow-x: auto;
}

/* Search + length controls (DataTables) */
.dt-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: .6rem;
  flex-wrap: wrap;
  gap: .5rem;
}
.dt-controls input[type=search] {
  padding: .35rem .7rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: .82rem;
  width: 260px;
}
.dt-controls select {
  padding: .3rem .5rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: .82rem;
}

/* Table */
table {
  width: 100%;
  border-collapse: collapse;
  font-size: .78rem;
  min-width: 1600px;
}
thead th {
  background: #1a3a6b;
  color: #fff;
  padding: .55rem .5rem;
  white-space: nowrap;
  font-size: .74rem;
  font-weight: 600;
  border-bottom: 3px solid #c8a951;
  cursor: pointer;
  user-select: none;
  position: sticky;
  top: 0;
  z-index: 10;
}
thead th::after { content: " ⇅"; opacity: .5; font-size:.65rem; }
thead th.asc::after  { content: " ↑"; opacity: 1; }
thead th.desc::after { content: " ↓"; opacity: 1; }

tbody tr { border-bottom: 1px solid #eee; }
tbody tr:hover { background: #eef3fb; }
tbody td { padding: .45rem .5rem; vertical-align: middle; white-space: nowrap; }

.col-rank { font-weight:700; color:#1a3a6b; text-align:center; }
a.earth-link:hover { color:#1a73e8 !important; text-decoration:underline; }
a.blog-link { color:inherit; text-decoration:none; }
a.blog-link:hover { color:#1a73e8 !important; text-decoration:underline; }
.ai-est   { background: #fff8e1; color: #7a5e00; }
.text-center { text-align: center; }
.text-right  { text-align: right; }
.na { color: #ccc; font-size: .72rem; }

/* Pills */
.pill { border-radius:4px; padding:2px 7px; font-size:.7rem; font-weight:700; }
.pill-req  { background:#dc3545; color:#fff; }
.pill-opt  { background:#0d6efd; color:#fff; }
.pill-bld  { background:#198754; color:#fff; }
.pill-ed   { background:#6f42c1; color:#fff; margin-right:2px; }
.pill-ea   { background:#fd7e14; color:#fff; }
.pill-rea  { background:#20c997; color:#fff; }
.pill-rd   { background:#adb5bd; color:#fff; }
.defer-yes { color:#dc3545; font-weight:700; }
.defer-no  { color:#198754; font-weight:700; }

/* Pagination */
.pagination { display:flex; gap:4px; justify-content:flex-end; margin-top:.7rem; flex-wrap:wrap; }
.pg-btn {
  padding: .28rem .65rem;
  border:1px solid #1a3a6b;
  border-radius:4px;
  background:#fff;
  color:#1a3a6b;
  cursor:pointer;
  font-size:.78rem;
}
.pg-btn.active { background:#1a3a6b; color:#fff; }
.pg-btn:disabled { opacity:.4; cursor:default; }

.legend { font-size:.72rem; color:#888; margin-top:.5rem; }
"""

# ── Helper: one data cell ────────────────────────────────────────────────────

def _cell(value, ai=False, cls="", right=False):
    """Return a <td> HTML string."""
    center = ' text-center' if not right else ' text-right'
    ai_cls = ' ai-est' if ai else ''
    extra  = f' {cls}' if cls else ''
    if value is None or value == "":
        inner = '<span class="na">—</span>'
        ai_cls = ''  # no yellow bg for empty cells
    else:
        inner = str(value)
    return f'<td class="{center}{ai_cls}{extra}">{inner}</td>'


def _test_pill(policy):
    if not policy:
        return '<span class="na">—</span>'
    p = policy.strip()
    suffix = ""
    if p.endswith("*"):
        suffix = " *"
        p = p[:-1].strip()

    if p == "Required":
        return f'<span class="pill pill-req">Required</span>{suffix}'
    if p == "Optional":
        return f'<span class="pill pill-opt">Optional</span>{suffix}'
    if p in ("Blind", "Test-Blind"):
        return f'<span class="pill pill-bld">Test-Blind</span>{suffix}'
    return policy


def _edea_pill(has_ed, has_ea, has_rea):
    parts = []
    if has_rea:
        parts.append('<span class="pill pill-rea">REA</span>')
    if has_ed:
        parts.append('<span class="pill pill-ed">ED</span>')
    if has_ea:
        parts.append('<span class="pill pill-ea">EA</span>')
    if not parts:
        return '<span class="pill pill-rd">RD Only</span>'
    return " ".join(parts)


def _defer_span(defer):
    if defer == "Yes":
        return '<span class="defer-yes">Yes</span>'
    if defer == "No":
        return '<span class="defer-no">No</span>'
    return '<span class="na">—</span>'


# ── Row builder ─────────────────────────────────────────────────────────────

def _build_row(r: dict, num: int = 0) -> str:
    # Rank (AI)
    rank_raw = r.get("_rank_raw")
    rank_disp = f"{rank_raw} ★" if rank_raw else None

    # GPA (AI)
    gpa_raw = r.get("_gpa_raw")
    gpa_disp = f"{gpa_raw:.2f} ★" if gpa_raw else None

    # ED/EA/REA cells
    has_ed  = r.get("_has_ed",  False)
    has_ea  = r.get("_has_ea",  False)
    has_rea = r.get("_has_rea", False)
    edea_html = _edea_pill(has_ed, has_ea, has_rea)

    # Due date (AI)
    due_raw = r.get("_due_date_raw")
    if due_raw:
        due_disp = due_raw
    else:
        ed_dl  = r.get("_ed_deadline")
        ea_dl  = r.get("_ea_deadline")
        rea_dl = r.get("_rea_deadline")
        due_parts = []
        if has_rea and rea_dl:
            due_parts.append(f"REA: {rea_dl}")
        if has_ed and ed_dl:
            due_parts.append(f"ED: {ed_dl}")
        if has_ea and ea_dl:
            due_parts.append(f"EA: {ea_dl}")
        due_disp = " / ".join(due_parts) if due_parts else None

    # Early rate (AI)
    early_raw = r.get("_early_rate_raw")
    if isinstance(early_raw, str):
        early_disp = early_raw
    else:
        early_disp = f"{early_raw:.1f}% ★" if early_raw is not None else None

    NA = '<span class="na">—</span>'
    cells = []
    # 1. Row number
    cells.append(f'<td class="col-rank">{num}</td>')
    # 2. Name (State) – name links to blog (if available), state links to Google Earth
    _blog_url = _BLOG_URLS.get(r["name"])
    _earth_query = f'{r["name"]}+{r["state"]}'.replace(' ', '+')
    _earth_url = f'https://earth.google.com/web/search/{_earth_query}'
    if _blog_url:
        _name_html = (f'<a class="blog-link" href="{_blog_url}" target="_top" '
                      f'title="블로그 가이드 보기"><strong>{r["name"]}</strong></a>')
    else:
        _name_html = f'<strong>{r["name"]}</strong>'
    cells.append(f'<td>{_name_html} '
                 f'<a class="earth-link" href="{_earth_url}" target="_top" '
                 f'title="Google Earth에서 보기" '
                 f'style="color:#888;text-decoration:none;cursor:pointer">'
                 f'({r["state"]})</a></td>')
    # 3. GPA (AI)
    cells.append(_cell(gpa_disp, ai=bool(gpa_raw)))
    # 4. SAT/ACT (official)
    cells.append(_cell(r.get("sat_act"), ai=bool(r.get("_sat_act_ai"))))
    # 5. Test policy (AI)
    ai_tp = bool(r.get("_test_policy_raw"))
    cells.append(f'<td class="text-center{"  ai-est" if ai_tp else ""}">'
                 f'{_test_pill(r.get("_test_policy_raw"))}</td>')
    # 6. Acceptance rate (Gemini primary)
    cells.append(_cell(r.get("acceptance_rate"), ai=bool(r.get("_acc_ai"))))
    # 7. ED/EA (AI)
    cells.append(f'<td class="text-center ai-est">{edea_html}</td>')
    # 8. Due date (AI)
    cells.append(_cell(due_disp, ai=bool(due_disp)))
    # 9. Early accept rate (AI)
    cells.append(_cell(early_disp, ai=bool(early_raw)))
    # 10. Enrollment (Gemini primary)
    cells.append(_cell(r.get("enrollment"), ai=bool(r.get("_enrollment_ai")), right=True))
    # 11. Ratio (Gemini primary)
    cells.append(_cell(r.get("ratio"), ai=bool(r.get("_ratio_ai"))))
    # 12. Tuition (Gemini primary)
    cells.append(_cell(r.get("tuition"), ai=bool(r.get("_tuition_ai")), right=True))
    # 13. Room & Board (Gemini primary)
    cells.append(_cell(r.get("room_board"), ai=bool(r.get("_tuition_ai")), right=True))
    # 14. Total Tuition (Gemini primary)
    ai_flag = ' ai-est' if r.get("_tuition_ai") else ''
    total_val = r.get("total_tuition") or NA
    cells.append(f'<td class="text-right{ai_flag}"><strong>{total_val}</strong></td>')
    # 15. Setting (official)
    cells.append(_cell(r.get("setting")))
    # 16. Defer (AI)
    defer_val = r.get("defer")
    cells.append(f'<td class="text-center{"  ai-est" if defer_val else ""}">'
                 f'{_defer_span(defer_val)}</td>')

    return "<tr>" + "".join(cells) + "</tr>"


# ── Table builder ────────────────────────────────────────────────────────────

def _build_table(tid: str, rows: list[dict]) -> str:
    headers = [
        ("Rank", "col-rank"),
        ("University / College (State)", ""),
        ("Avg GPA<br><small>(W. Fresh.)</small>", ""),
        ("SAT / ACT<br><small>Midpoint</small>", ""),
        ("Test Policy", ""),
        ("Accept. Rate<br><small>Regular</small>", ""),
        ("ED/EA/REA", ""),
        ("Due Date<br><small>ED/EA/REA</small>", ""),
        ("Accept. Rate<br><small>Early</small>", ""),
        ("Total<br>Enrollment", ""),
        ("Student:<br>Faculty", ""),
        ("Tuition<br><small>In / Out-of-State</small>", ""),
        ("Room &amp;<br>Board", ""),
        ("Total<br>Tuition", ""),
        ("Setting", ""),
        ("Defer", ""),
    ]
    th_html = "".join(
        f'<th data-col="{i}" class="{cls}">{label}</th>'
        for i, (label, cls) in enumerate(headers)
    )
    rows_html = "\n".join(_build_row(r, i+1) for i, r in enumerate(rows))
    return f"""
<div class="dt-controls">
  <div>
    Show <select id="len-{tid}" onchange="changeLen('{tid}',this.value)">
      <option value="25">25</option>
      <option value="50" selected>50</option>
      <option value="100">100</option>
      <option value="9999">All</option>
    </select> schools
  </div>
  <input type="search" id="search-{tid}" placeholder="🔍 Filter schools..." oninput="filterTable('{tid}')" />
</div>
<table id="tbl-{tid}">
  <thead><tr>{th_html}</tr></thead>
  <tbody id="tbody-{tid}">{rows_html}</tbody>
</table>
<div class="pagination" id="pg-{tid}"></div>
<div class="legend">
  ★ = AI-estimated via Gemini (highlighted in yellow) — verify before use &nbsp;|&nbsp;
  Official data: US Dept. of Education College Scorecard
</div>"""


# ── JavaScript ───────────────────────────────────────────────────────────────

_JS = """
// Tab switching
function showTab(tid) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('panel-' + tid).classList.add('active');
  document.querySelector('[data-tab="' + tid + '"]').classList.add('active');
}

// Per-table state
const state = {};

function getState(tid) {
  if (!state[tid]) {
    const tbody = document.getElementById('tbody-' + tid);
    state[tid] = {
      allRows: Array.from(tbody.querySelectorAll('tr')),
      filtered: [],
      page: 1,
      pageLen: 50,
      sortCol: 0,
      sortDir: 'asc',
    };
    state[tid].filtered = [...state[tid].allRows];
  }
  return state[tid];
}

function filterTable(tid) {
  const q = document.getElementById('search-' + tid).value.toLowerCase();
  const s = getState(tid);
  s.filtered = s.allRows.filter(tr => tr.textContent.toLowerCase().includes(q));
  s.page = 1;
  render(tid);
}

function changeLen(tid, v) {
  const s = getState(tid);
  s.pageLen = parseInt(v);
  s.page = 1;
  render(tid);
}

function sortTable(tid, col) {
  const s = getState(tid);
  if (s.sortCol === col) {
    s.sortDir = s.sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    s.sortCol = col;
    s.sortDir = 'asc';
  }
  const dir = s.sortDir === 'asc' ? 1 : -1;
  s.filtered.sort((a, b) => {
    const at = a.cells[col]?.textContent.trim() || '';
    const bt = b.cells[col]?.textContent.trim() || '';
    const an = parseFloat(at.replace(/[^0-9.\-]/g, ''));
    const bn = parseFloat(bt.replace(/[^0-9.\-]/g, ''));
    if (!isNaN(an) && !isNaN(bn)) return (an - bn) * dir;
    if (at === '—' || at === '') return 1;
    if (bt === '—' || bt === '') return -1;
    return at.localeCompare(bt) * dir;
  });
  // Update header arrows
  document.querySelectorAll('#tbl-' + tid + ' thead th').forEach((th, i) => {
    th.classList.remove('asc', 'desc');
    if (i === col) th.classList.add(s.sortDir);
  });
  s.page = 1;
  render(tid);
}

function render(tid) {
  const s = getState(tid);
  const tbody = document.getElementById('tbody-' + tid);
  const total = s.filtered.length;
  const pages = s.pageLen >= 9999 ? 1 : Math.ceil(total / s.pageLen);
  s.page = Math.min(s.page, pages || 1);
  const start = (s.page - 1) * (s.pageLen >= 9999 ? total : s.pageLen);
  const end   = s.pageLen >= 9999 ? total : Math.min(start + s.pageLen, total);

  tbody.innerHTML = '';
  s.filtered.slice(start, end).forEach(tr => tbody.appendChild(tr));

  // Pagination buttons
  const pg = document.getElementById('pg-' + tid);
  pg.innerHTML = '';
  if (pages <= 1) return;
  const mkBtn = (label, page, disabled, active) => {
    const b = document.createElement('button');
    b.className = 'pg-btn' + (active ? ' active' : '');
    b.textContent = label;
    b.disabled = disabled;
    if (!disabled) b.onclick = () => { s.page = page; render(tid); };
    return b;
  };
  pg.appendChild(mkBtn('«', 1, s.page === 1, false));
  pg.appendChild(mkBtn('‹', s.page - 1, s.page === 1, false));
  const win = 2;
  for (let p = Math.max(1, s.page - win); p <= Math.min(pages, s.page + win); p++) {
    pg.appendChild(mkBtn(p, p, false, p === s.page));
  }
  pg.appendChild(mkBtn('›', s.page + 1, s.page === pages, false));
  pg.appendChild(mkBtn('»', pages, s.page === pages, false));
}

// Wire up sort clicks
document.addEventListener('DOMContentLoaded', () => {
  ['national', 'lac'].forEach(tid => {
    getState(tid);  // init
    render(tid);
    document.querySelectorAll('#tbl-' + tid + ' thead th').forEach((th, i) => {
      th.addEventListener('click', () => sortTable(tid, i));
    });
  });
});
"""


# ── Public: build full HTML ──────────────────────────────────────────────────

def build_html(national_rows: list[dict], lac_rows: list[dict],
               scorecard_age: str, gemini_age: str,
               days_until_refresh: int = 0) -> str:
    nat_table = _build_table("national", national_rows)
    lac_table = _build_table("lac", lac_rows)
    now = datetime.now().strftime("%B %d, %Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Elite U.S. College Data Sheet</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>{_CSS}</style>
</head>
<body>

<header class="site-header">
  <div>
    <h1>🎓 Elite U.S. College Data Sheet</h1>
    <sub>Top 100 National Universities &amp; Top 100 Liberal Arts Colleges · 2025–2026</sub>
  </div>
  <div class="updated">
    Generated: {now}<br/>
    🔁 Auto-refresh in: <strong>{days_until_refresh} days</strong><br/>
    Scorecard: {scorecard_age} · Gemini: {gemini_age}
    <div style="display:flex;gap:6px;justify-content:flex-end;margin-top:8px;">
      <button class="header-btn" onclick="window.top.location.href='/?action=refresh'">🔄 갱신</button>
      <button class="header-btn" onclick="window.top.location.href='/?action=force_refresh'">⚡ 강제 갱신</button>
    </div>
  </div>
</header>

<div class="info-bar">
  <span>📡 Official data (College Scorecard): <strong>{scorecard_age}</strong></span>
  <span>🤖 AI estimates (Gemini): <strong>{gemini_age}</strong></span>
  <span><span class="ai-badge">★ AI Est.</span> Yellow = AI-estimated · verify before use</span>
</div>

<div class="tabs">
  <button class="tab-btn active" data-tab="national" onclick="showTab('national')">
    🏛 National Universities ({len(national_rows)})
  </button>
  <button class="tab-btn" data-tab="lac" onclick="showTab('lac')">
    🌿 Liberal Arts Colleges ({len(lac_rows)})
  </button>
</div>

<div id="panel-national" class="tab-panel active">
  <div class="table-wrap">{nat_table}</div>
</div>

<div id="panel-lac" class="tab-panel">
  <div class="table-wrap">{lac_table}</div>
</div>

<script>{_JS}</script>
</body>
</html>"""
