import os
import sys
import streamlit as st

# Make sure root is on the path regardless of which page is running
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from db.schema import get_connection, DB_PATH  # re-export

# ── Risk colours & labels ─────────────────────────────────────────────────────

RISK_COLORS = {
    "VERY_HIGH": "#C53030",
    "HIGH":      "#DD6B20",
    "MEDIUM":    "#D69E2E",
    "LOW":       "#38A169",
}

RISK_BG = {
    "VERY_HIGH": "#FFF5F5",
    "HIGH":      "#FFFAF0",
    "MEDIUM":    "#FFFFF0",
    "LOW":       "#F0FFF4",
}

RISK_LABELS = {
    "VERY_HIGH": "Very High",
    "HIGH":      "High",
    "MEDIUM":    "Moderate",
    "LOW":       "Low",
}

FULCRUM_BLUE = "#2B6CB0"

# ── Shared CSS ────────────────────────────────────────────────────────────────

PAGE_CSS = """
<style>
/* Global font */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Hide Streamlit default menu & footer for clean demo */
#MainMenu {visibility: hidden;}
footer    {visibility: hidden;}

/* Metric cards */
div[data-testid="metric-container"] {
    background: #F7FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 12px 16px;
}

/* Dataframe header colour */
thead tr th { background-color: #EBF8FF !important; }

/* Risk badge pill */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    color: white;
}
.badge-VERY_HIGH { background: #C53030; }
.badge-HIGH      { background: #DD6B20; }
.badge-MEDIUM    { background: #D69E2E; }
.badge-LOW       { background: #38A169; }

/* Feed item */
.feed-item {
    border-left: 3px solid #4299E1;
    padding: 8px 12px;
    margin-bottom: 8px;
    background: #EBF8FF;
    border-radius: 0 6px 6px 0;
    font-size: 13px;
}
.feed-item.completed { border-color: #48BB78; background: #F0FFF4; }
.feed-item.warning   { border-color: #ED8936; background: #FFFAF0; }

/* Section headers */
.section-header {
    font-size: 15px;
    font-weight: 700;
    color: #2D3748;
    border-bottom: 2px solid #E2E8F0;
    padding-bottom: 4px;
    margin-bottom: 12px;
}
</style>
"""

def apply_css():
    st.markdown(PAGE_CSS, unsafe_allow_html=True)

def brand_header(subtitle: str = ""):
    st.markdown(
        f"<span style='font-size:22px;font-weight:700;color:{FULCRUM_BLUE}'>🦷 FulcrumCare</span>"
        + (f"&nbsp;&nbsp;<span style='font-size:14px;color:#718096'>{subtitle}</span>" if subtitle else ""),
        unsafe_allow_html=True,
    )

def risk_badge(bucket: str) -> str:
    label = RISK_LABELS.get(bucket, bucket)
    return f"<span class='badge badge-{bucket}'>{label}</span>"

def risk_color(bucket: str) -> str:
    return RISK_COLORS.get(bucket, "#718096")

def ensure_seeded():
    """Auto-seed on first launch if DB is empty."""
    if not os.path.exists(DB_PATH):
        _run_seed()
        return
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    conn.close()
    if count == 0:
        _run_seed()

def _run_seed():
    from db.seed import seed_database
    seed_database()

def fmt_date(d: str) -> str:
    if not d:
        return "—"
    try:
        from datetime import datetime
        return datetime.fromisoformat(d[:10]).strftime("%b %d, %Y")
    except Exception:
        return d

def fmt_datetime(d: str) -> str:
    if not d:
        return "—"
    try:
        from datetime import datetime
        return datetime.fromisoformat(d).strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return d

def age_from_dob(dob: str) -> int:
    from datetime import date
    try:
        b = date.fromisoformat(dob)
        today = date.today()
        return today.year - b.year - ((today.month, today.day) < (b.month, b.day))
    except Exception:
        return 0
