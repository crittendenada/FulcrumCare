import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.helpers import (
    apply_css, ensure_seeded, get_connection,
    RISK_COLORS, RISK_LABELS,
)

st.set_page_config(page_title="Admin – FulcrumCare", page_icon="📊", layout="wide")
apply_css()
ensure_seeded()

with st.sidebar:
    st.markdown(
        "<div style='font-size:18px;font-weight:800;color:#2B6CB0'>🦷 FulcrumCare</div>"
        "<div style='font-size:11px;color:#718096'>Population Health Admin</div>",
        unsafe_allow_html=True,
    )
    st.divider()
    st.caption("Read-only analytics view")
    st.divider()

    conn_s = get_connection()
    clinics_df = pd.read_sql_query("SELECT clinic_id, name FROM clinics", conn_s)
    conn_s.close()
    clinic_options = {"All Clinics": None} | {r["name"]: r["clinic_id"] for _, r in clinics_df.iterrows()}
    sel_clinic_name = st.selectbox("Filter by Clinic", list(clinic_options.keys()))
    sel_clinic_id   = clinic_options[sel_clinic_name]

st.markdown(
    "<h2 style='margin-bottom:2px'>Population Health Dashboard</h2>"
    "<p style='color:#718096;margin-top:0'>Program-level analytics across all enrolled Medicaid patients.</p>",
    unsafe_allow_html=True,
)

conn = get_connection()

# ── Build optional clinic filter ─────────────────────────────────────────────
clinic_join   = "JOIN providers pv ON p.assigned_provider_id = pv.provider_id" if sel_clinic_id else ""
clinic_where  = f"AND pv.clinic_id = {sel_clinic_id}" if sel_clinic_id else ""


# ── KPI Row ───────────────────────────────────────────────────────────────────
total = conn.execute(
    f"SELECT COUNT(*) FROM patients p {clinic_join} WHERE p.is_active=1 {clinic_where}"
).fetchone()[0]
open_gaps = conn.execute(
    f"""SELECT COUNT(*) FROM care_gaps cg
        JOIN patients p ON cg.patient_id=p.patient_id
        {clinic_join}
        WHERE cg.gap_status='OPEN' {clinic_where}"""
).fetchone()[0]
closed_gaps = conn.execute(
    f"""SELECT COUNT(*) FROM care_gaps cg
        JOIN patients p ON cg.patient_id=p.patient_id
        {clinic_join}
        WHERE cg.gap_status='CLOSED' {clinic_where}"""
).fetchone()[0]
high_risk = conn.execute(
    f"""SELECT COUNT(*) FROM patient_risk_profile pr
        JOIN patients p ON pr.patient_id=p.patient_id
        {clinic_join}
        WHERE pr.risk_bucket IN ('HIGH','VERY_HIGH') {clinic_where}"""
).fetchone()[0]
diabetic_pct = conn.execute(
    f"SELECT ROUND(100.0*SUM(p.is_diabetic)/COUNT(*),1) FROM patients p {clinic_join} WHERE p.is_active=1 {clinic_where}"
).fetchone()[0] or 0
tasks_open = conn.execute("SELECT COUNT(*) FROM care_tasks WHERE status='OPEN'").fetchone()[0]

total_gaps = open_gaps + closed_gaps
closure_rate = round(closed_gaps / max(total_gaps, 1) * 100, 1)

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Total Patients",     total)
m2.metric("Open Care Gaps",     open_gaps)
m3.metric("Gap Closure Rate",   f"{closure_rate}%",
          delta=f"{closed_gaps} closed", delta_color="normal")
m4.metric("High / Very High Risk", high_risk,
          delta=f"{round(high_risk/max(total,1)*100)}% of pop", delta_color="inverse")
m5.metric("Diabetic Patients",  f"{diabetic_pct}%")
m6.metric("Open Coordinator Tasks", tasks_open)

st.divider()

# ── Row 1: Measure Trends + Risk Distribution ─────────────────────────────────
row1_l, row1_r = st.columns([3, 2])

with row1_l:
    st.markdown("<div class='section-header'>Care Gap Counts by Measure</div>", unsafe_allow_html=True)
    gap_by_measure = pd.read_sql_query(
        f"""SELECT mr.name as measure, cg.gap_status, COUNT(*) as count
            FROM care_gaps cg
            JOIN measure_reference mr ON cg.measure_id = mr.measure_id
            JOIN patients p ON cg.patient_id = p.patient_id
            {clinic_join}
            WHERE 1=1 {clinic_where}
            GROUP BY mr.name, cg.gap_status
            ORDER BY mr.name""",
        conn,
    )
    if not gap_by_measure.empty:
        fig = px.bar(
            gap_by_measure, x="count", y="measure", color="gap_status",
            orientation="h", barmode="stack",
            color_discrete_map={"OPEN": "#E53E3E", "CLOSED": "#38A169", "NOT_APPLICABLE": "#CBD5E0"},
            labels={"count": "Patients", "measure": "", "gap_status": "Status"},
            height=280,
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            plot_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True)

with row1_r:
    st.markdown("<div class='section-header'>Risk Tier Distribution</div>", unsafe_allow_html=True)
    risk_dist = pd.read_sql_query(
        f"""SELECT pr.risk_bucket, COUNT(*) as count
            FROM patient_risk_profile pr
            JOIN patients p ON pr.patient_id = p.patient_id
            {clinic_join}
            WHERE 1=1 {clinic_where}
            GROUP BY pr.risk_bucket""",
        conn,
    )
    if not risk_dist.empty:
        risk_dist["label"] = risk_dist["risk_bucket"].map(RISK_LABELS)
        order = ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
        risk_dist["sort"] = risk_dist["risk_bucket"].map({b: i for i, b in enumerate(order)})
        risk_dist = risk_dist.sort_values("sort")
        fig2 = px.pie(
            risk_dist, values="count", names="label",
            color="risk_bucket",
            color_discrete_map={k: RISK_COLORS[k] for k in RISK_COLORS},
            hole=0.45,
            height=280,
        )
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(margin=dict(l=0, r=0, t=10, b=0),
                           showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

# ── Row 2: ADI distribution + Measure compliance rates ───────────────────────
row2_l, row2_r = st.columns(2)

with row2_l:
    st.markdown("<div class='section-header'>Population by ADI Decile</div>", unsafe_allow_html=True)
    adi_dist = pd.read_sql_query(
        f"""SELECT p.adi_decile,
               COUNT(*) as total,
               SUM(CASE WHEN pr.risk_bucket IN ('HIGH','VERY_HIGH') THEN 1 ELSE 0 END) as high_risk
            FROM patients p
            {clinic_join}
            LEFT JOIN patient_risk_profile pr ON p.patient_id = pr.patient_id
            WHERE p.is_active=1 {clinic_where}
            GROUP BY p.adi_decile ORDER BY p.adi_decile""",
        conn,
    )
    if not adi_dist.empty:
        fig3 = go.Figure()
        fig3.add_bar(x=adi_dist["adi_decile"].astype(str), y=adi_dist["total"],
                     name="Total", marker_color="#BEE3F8")
        fig3.add_bar(x=adi_dist["adi_decile"].astype(str), y=adi_dist["high_risk"],
                     name="High/Very High Risk", marker_color="#E53E3E")
        fig3.update_layout(
            barmode="overlay",
            xaxis_title="ADI Decile (10 = most deprived)",
            yaxis_title="Patients",
            height=260,
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig3, use_container_width=True)

with row2_r:
    st.markdown("<div class='section-header'>Measure Compliance Rates</div>", unsafe_allow_html=True)
    compliance = pd.read_sql_query(
        f"""SELECT mr.name as measure,
               COUNT(*) as total,
               SUM(CASE WHEN cg.gap_status='CLOSED' THEN 1 ELSE 0 END) as closed,
               ROUND(100.0*SUM(CASE WHEN cg.gap_status='CLOSED' THEN 1 ELSE 0 END)/COUNT(*),1) as pct
            FROM care_gaps cg
            JOIN measure_reference mr ON cg.measure_id = mr.measure_id
            JOIN patients p ON cg.patient_id = p.patient_id
            {clinic_join}
            WHERE cg.gap_status != 'NOT_APPLICABLE' {clinic_where}
            GROUP BY mr.name
            ORDER BY pct DESC""",
        conn,
    )
    if not compliance.empty:
        fig4 = px.bar(
            compliance, x="pct", y="measure", orientation="h",
            labels={"pct": "Compliance %", "measure": ""},
            color="pct",
            color_continuous_scale=["#E53E3E", "#ED8936", "#38A169"],
            range_color=[0, 100],
            height=260,
        )
        fig4.update_coloraxes(showscale=False)
        fig4.update_traces(text=compliance["pct"].map(lambda x: f"{x}%"),
                           textposition="outside")
        fig4.update_layout(margin=dict(l=0, r=0, t=10, b=0),
                           xaxis_range=[0, 115],
                           plot_bgcolor="white")
        st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ── Row 3: Provider performance table ─────────────────────────────────────────
st.markdown("<div class='section-header'>Provider Performance Overview</div>", unsafe_allow_html=True)

prov_perf = pd.read_sql_query(
    f"""SELECT prov.name as provider, cl.name as clinic,
           COUNT(DISTINCT p.patient_id) as patients,
           COUNT(DISTINCT CASE WHEN cg.gap_status='OPEN' THEN cg.gap_id END) as open_gaps,
           COUNT(DISTINCT CASE WHEN cg.gap_status='CLOSED' THEN cg.gap_id END) as closed_gaps,
           ROUND(100.0 *
               COUNT(DISTINCT CASE WHEN cg.gap_status='CLOSED' THEN cg.gap_id END) /
               NULLIF(COUNT(DISTINCT cg.gap_id),0), 1) as closure_pct,
           ROUND(AVG(pr.composite_risk),1) as avg_risk
        FROM providers prov
        JOIN clinics cl ON prov.clinic_id = cl.clinic_id
        JOIN patients p ON p.assigned_provider_id = prov.provider_id
        LEFT JOIN care_gaps cg ON cg.patient_id = p.patient_id
        LEFT JOIN patient_risk_profile pr ON pr.patient_id = p.patient_id
        WHERE p.is_active=1
        GROUP BY prov.provider_id
        ORDER BY patients DESC""",
    conn,
)
if not prov_perf.empty:
    prov_perf.columns = ["Provider", "Clinic", "Patients", "Open Gaps", "Closed Gaps", "Closure %", "Avg Risk Score"]
    st.dataframe(prov_perf, use_container_width=True, hide_index=True)

st.divider()

# ── Row 4: Outreach activity summary + data quality ───────────────────────────
dq_l, dq_r = st.columns(2)

with dq_l:
    st.markdown("<div class='section-header'>Outreach Activity (Last 30 Days)</div>", unsafe_allow_html=True)
    outreach_summary = pd.read_sql_query(
        """SELECT method,
               COUNT(*) as attempts,
               SUM(CASE WHEN outcome='reached' THEN 1 ELSE 0 END) as reached,
               ROUND(100.0*SUM(CASE WHEN outcome='reached' THEN 1 ELSE 0 END)/COUNT(*),1) as reach_rate
           FROM outreach_attempts
           WHERE attempt_time >= date('now','-30 days')
           GROUP BY method ORDER BY attempts DESC""",
        conn,
    )
    if outreach_summary.empty:
        st.caption("No outreach in the last 30 days.")
    else:
        outreach_summary.columns = ["Method", "Attempts", "Reached", "Reach Rate %"]
        st.dataframe(outreach_summary, use_container_width=True, hide_index=True)

    st.markdown("<div class='section-header' style='margin-top:16px'>Recent Care Task Activity</div>",
                unsafe_allow_html=True)
    task_summary = pd.read_sql_query(
        """SELECT status, COUNT(*) as count FROM care_tasks GROUP BY status""", conn
    )
    if not task_summary.empty:
        task_summary.columns = ["Status", "Count"]
        st.dataframe(task_summary, use_container_width=True, hide_index=True)

with dq_r:
    st.markdown("<div class='section-header'>Data Quality & System Integrity</div>", unsafe_allow_html=True)

    no_sdoh = conn.execute(
        "SELECT COUNT(*) FROM patients p WHERE NOT EXISTS "
        "(SELECT 1 FROM sdoh_assessment s WHERE s.patient_id=p.patient_id) AND p.is_active=1"
    ).fetchone()[0]
    no_risk = conn.execute(
        "SELECT COUNT(*) FROM patients p WHERE NOT EXISTS "
        "(SELECT 1 FROM patient_risk_profile pr WHERE pr.patient_id=p.patient_id) AND p.is_active=1"
    ).fetchone()[0]
    no_gaps = conn.execute(
        "SELECT COUNT(*) FROM patients p WHERE NOT EXISTS "
        "(SELECT 1 FROM care_gaps cg WHERE cg.patient_id=p.patient_id) AND p.is_active=1"
    ).fetchone()[0]
    sdoh_pct    = round((1 - no_sdoh / max(total, 1)) * 100, 1)
    risk_pct    = round((1 - no_risk / max(total, 1)) * 100, 1)
    gaps_pct    = round((1 - no_gaps / max(total, 1)) * 100, 1)

    def dq_row(label, pct):
        color = "#38A169" if pct >= 95 else "#D69E2E" if pct >= 80 else "#E53E3E"
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;padding:6px 0;"
            f"border-bottom:1px solid #EDF2F7'>"
            f"<span>{label}</span>"
            f"<span style='font-weight:700;color:{color}'>{pct}%</span></div>",
            unsafe_allow_html=True,
        )

    dq_row("SDOH Assessment Coverage", sdoh_pct)
    dq_row("Risk Profile Coverage",    risk_pct)
    dq_row("Care Gap Evaluation Coverage", gaps_pct)

    st.markdown("<br>", unsafe_allow_html=True)

    # Engagement distribution
    eng_dist = pd.read_sql_query(
        """SELECT
               SUM(CASE WHEN NOT EXISTS(SELECT 1 FROM outreach_attempts oa WHERE oa.patient_id=p.patient_id) THEN 1 ELSE 0 END) as never_contacted,
               SUM(CASE WHEN EXISTS(SELECT 1 FROM outreach_attempts oa WHERE oa.patient_id=p.patient_id AND oa.outcome='reached') THEN 1 ELSE 0 END) as reached,
               SUM(CASE WHEN EXISTS(SELECT 1 FROM engagement_events ee WHERE ee.patient_id=p.patient_id AND ee.event_type='appt_scheduled') THEN 1 ELSE 0 END) as appt_scheduled
           FROM patients p WHERE p.is_active=1""",
        conn,
    ).iloc[0]
    st.caption("**Engagement Breakdown (all-time)**")
    ec1, ec2, ec3 = st.columns(3)
    ec1.metric("Never Contacted", int(eng_dist["never_contacted"]))
    ec2.metric("Reached",         int(eng_dist["reached"]))
    ec3.metric("Appt Scheduled",  int(eng_dist["appt_scheduled"]))

conn.close()
