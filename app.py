import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st

st.set_page_config(
    page_title="FulcrumCare",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.helpers import apply_css, ensure_seeded, get_connection

apply_css()
ensure_seeded()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='font-size:20px;font-weight:800;color:#2B6CB0'>🦷 FulcrumCare</div>"
        "<div style='font-size:11px;color:#718096;margin-bottom:16px'>"
        "Preventive dental → better outcomes</div>",
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("**Demo Controls**")
    if st.button("🔄 Reset Demo Data", use_container_width=True):
        from db.seed import seed_database
        with st.spinner("Rebuilding demo dataset…"):
            seed_database()
        st.success("Demo data reset!")
        st.rerun()

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='color:#2B6CB0;margin-bottom:4px'>🦷 FulcrumCare</h1>"
    "<p style='font-size:18px;color:#4A5568;margin-top:0'>"
    "Connecting preventive dental care to better health outcomes for Medicaid patients.</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── Role cards ────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

CARD = """
<div style='background:{bg};border:1px solid {border};border-radius:10px;
            padding:20px 24px;min-height:180px'>
  <div style='font-size:32px'>{icon}</div>
  <div style='font-size:17px;font-weight:700;color:#2D3748;margin:6px 0 4px'>{title}</div>
  <div style='font-size:13px;color:#718096;line-height:1.5'>{desc}</div>
</div>
"""

with col1:
    st.markdown(CARD.format(
        bg="#EBF8FF", border="#BEE3F8", icon="👨‍⚕️",
        title="Clinician View",
        desc="Monitor care gaps and priority actions across your attributed patient panel. "
             "Send tasks directly to care coordinators."
    ), unsafe_allow_html=True)
    st.page_link("pages/1_Clinician.py", label="Open Clinician View →", use_container_width=True)

with col2:
    st.markdown(CARD.format(
        bg="#F0FFF4", border="#C6F6D5", icon="👥",
        title="Care Coordinator View",
        desc="Manage outreach, track patient engagement, and complete tasks for your "
             "assigned population."
    ), unsafe_allow_html=True)
    st.page_link("pages/2_Care_Coordinator.py", label="Open Care Coordinator View →", use_container_width=True)

with col3:
    st.markdown(CARD.format(
        bg="#FFFFF0", border="#FAF089", icon="📊",
        title="Admin / Population Health",
        desc="Population-level analytics, measure trend tracking, provider performance, "
             "and data quality oversight."
    ), unsafe_allow_html=True)
    st.page_link("pages/3_Admin.py", label="Open Admin View →", use_container_width=True)

# ── Quick stats ───────────────────────────────────────────────────────────────
st.divider()
st.markdown("### Population Snapshot")

conn = get_connection()
total    = conn.execute("SELECT COUNT(*) FROM patients WHERE is_active=1").fetchone()[0]
open_gaps = conn.execute("SELECT COUNT(*) FROM care_gaps WHERE gap_status='OPEN'").fetchone()[0]
high_risk = conn.execute(
    "SELECT COUNT(*) FROM patient_risk_profile WHERE risk_bucket IN ('HIGH','VERY_HIGH')"
).fetchone()[0]
open_tasks = conn.execute("SELECT COUNT(*) FROM care_tasks WHERE status='OPEN'").fetchone()[0]
coord_week = conn.execute(
    "SELECT COUNT(*) FROM outreach_attempts WHERE attempt_time >= date('now','-7 days')"
).fetchone()[0]
conn.close()

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Patients",    total)
m2.metric("Open Care Gaps",    open_gaps)
m3.metric("High / Very High Risk", high_risk)
m4.metric("Open Coordinator Tasks", open_tasks)
m5.metric("Outreach This Week", coord_week)
