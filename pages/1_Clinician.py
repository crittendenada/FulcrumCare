import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st
import pandas as pd
from datetime import datetime

from utils.helpers import (
    apply_css, ensure_seeded, get_connection,
    risk_badge, risk_color, RISK_COLORS, RISK_LABELS, fmt_date, fmt_datetime,
)

st.set_page_config(page_title="Clinician – FulcrumCare", page_icon="👨‍⚕️", layout="wide")
apply_css()
ensure_seeded()

# ── Session state defaults ────────────────────────────────────────────────────
if "clin_view"    not in st.session_state: st.session_state.clin_view = "Patient Panel"
if "clin_patient" not in st.session_state: st.session_state.clin_patient = None
if "clin_provider" not in st.session_state: st.session_state.clin_provider = 1

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='font-size:18px;font-weight:800;color:#2B6CB0'>🦷 FulcrumCare</div>"
        "<div style='font-size:11px;color:#718096'>Clinician Portal</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    conn = get_connection()
    providers = pd.read_sql_query("SELECT provider_id, name, clinic_id FROM providers", conn)
    clinics   = pd.read_sql_query("SELECT clinic_id, name FROM clinics", conn)
    conn.close()

    prov_options = {row["name"]: row["provider_id"] for _, row in providers.iterrows()}
    selected_prov_name = st.selectbox("Viewing as", list(prov_options.keys()))
    st.session_state.clin_provider = prov_options[selected_prov_name]

    st.divider()
    view = st.radio(
        "Navigation",
        ["Patient Panel", "Patient Worklist", "Patient Record"],
        index=["Patient Panel", "Patient Worklist", "Patient Record"].index(st.session_state.clin_view),
    )
    st.session_state.clin_view = view


# ── Shared data for this provider ─────────────────────────────────────────────
@st.cache_data(ttl=0)
def load_provider_patients(provider_id):
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT p.patient_id, p.first_name, p.last_name, p.age, p.gender,
                  p.medicaid_id, p.is_diabetic, p.has_periodontitis,
                  p.assigned_coordinator_id,
                  pr.composite_risk, pr.risk_bucket,
                  cc.name as coordinator_name
           FROM patients p
           LEFT JOIN patient_risk_profile pr ON p.patient_id = pr.patient_id
           LEFT JOIN care_coordinators cc ON p.assigned_coordinator_id = cc.coordinator_id
           WHERE p.assigned_provider_id = ? AND p.is_active = 1
           ORDER BY pr.composite_risk DESC NULLS LAST""",
        conn, params=(provider_id,)
    )
    conn.close()
    return df


# ══════════════════════════════════════════════════════════════════════════════
# VIEW: PATIENT PANEL
# ══════════════════════════════════════════════════════════════════════════════
def view_patient_panel():
    prov_id = st.session_state.clin_provider
    patients = load_provider_patients(prov_id)

    conn = get_connection()

    st.markdown(
        "<h2 style='margin-bottom:2px'>Patient Panel Overview</h2>"
        "<p style='color:#718096;margin-top:0'>Monitor dental care gaps and engagement across your attributed patients.</p>",
        unsafe_allow_html=True,
    )

    # ── Measure KPI tiles ──────────────────────────────────────────────────────
    measures_of_interest = [
        ("PREV_DENTAL_12M",         "Preventive Dental Visit"),
        ("ORAL_EVAL_DIABETES",       "Oral Eval – Adults w/ Diabetes"),
        ("PERIODONTAL_EVAL",         "Periodontal Evaluation"),
    ]
    cols = st.columns(3)
    for i, (mid, mname) in enumerate(measures_of_interest):
        cnt = conn.execute(
            """SELECT COUNT(*) FROM care_gaps cg
               JOIN patients p ON cg.patient_id = p.patient_id
               WHERE cg.measure_id=? AND cg.gap_status='OPEN'
                 AND p.assigned_provider_id=?""",
            (mid, prov_id)
        ).fetchone()[0]
        cols[i].metric(mname, f"{cnt} patients", "need evaluation")

    st.divider()

    # ── Population stats ───────────────────────────────────────────────────────
    total  = len(patients)
    open_g = conn.execute(
        """SELECT COUNT(DISTINCT cg.patient_id) FROM care_gaps cg
           JOIN patients p ON cg.patient_id=p.patient_id
           WHERE cg.gap_status='OPEN' AND p.assigned_provider_id=?""", (prov_id,)
    ).fetchone()[0]
    hi_risk = len(patients[patients["risk_bucket"].isin(["HIGH", "VERY_HIGH"])])
    ed_cnt  = conn.execute(
        """SELECT COUNT(*) FROM encounters e
           JOIN patients p ON e.patient_id=p.patient_id
           WHERE e.encounter_type='ED' AND p.assigned_provider_id=?
             AND e.encounter_date >= date('now','-365 days')""", (prov_id,)
    ).fetchone()[0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Attributed Patients", total)
    m2.metric("Patients w/ Open Care Gaps", open_g, f"{round(open_g/max(total,1)*100)}% of panel")
    m3.metric("High / Very High Risk", hi_risk)
    m4.metric("ED Visits (Last 12 Mo)", ed_cnt)

    st.divider()

    # ── Priority Actions ───────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Priority Actions</div>", unsafe_allow_html=True)
    st.caption("Patients requiring immediate clinical attention — ordered by risk score")

    priority = patients[patients["risk_bucket"].isin(["HIGH", "VERY_HIGH"])].head(10).copy()

    if priority.empty:
        st.info("No high-risk patients on your panel right now.")
    else:
        for _, row in priority.iterrows():
            # Latest open gap for this patient
            gap_row = conn.execute(
                """SELECT mr.name FROM care_gaps cg
                   JOIN measure_reference mr ON cg.measure_id=mr.measure_id
                   WHERE cg.patient_id=? AND cg.gap_status='OPEN'
                   ORDER BY mr.priority_weight DESC LIMIT 1""",
                (row["patient_id"],)
            ).fetchone()
            gap_name = gap_row[0] if gap_row else "—"

            next_appt = conn.execute(
                """SELECT event_timestamp FROM engagement_events
                   WHERE patient_id=? AND event_type='appt_scheduled'
                   ORDER BY event_timestamp DESC LIMIT 1""",
                (row["patient_id"],)
            ).fetchone()
            appt_str = "Scheduled" if next_appt else "Not Scheduled"

            c1, c2, c3, c4, c5 = st.columns([3, 3, 1.5, 2, 1])
            with c1:
                sex_label = "M" if row["gender"] == "M" else "F"
                st.markdown(
                    f"**{row['first_name']} {row['last_name']}** &nbsp;"
                    f"<span style='color:#718096;font-size:12px'>{row['age']}{sex_label} · "
                    f"{row['medicaid_id']}</span>",
                    unsafe_allow_html=True,
                )
            c2.markdown(f"<span style='font-size:13px'>{gap_name}</span>", unsafe_allow_html=True)
            c3.markdown(risk_badge(row["risk_bucket"]), unsafe_allow_html=True)
            c4.markdown(
                f"<span style='font-size:12px;color:#718096'>{appt_str}</span>",
                unsafe_allow_html=True,
            )
            with c5:
                if st.button("View", key=f"view_{row['patient_id']}"):
                    st.session_state.clin_patient = int(row["patient_id"])
                    st.session_state.clin_view = "Patient Record"
                    st.rerun()
            st.markdown("<hr style='margin:4px 0;border-color:#EDF2F7'>", unsafe_allow_html=True)

    st.divider()

    # ── Care Coordinator Updates ───────────────────────────────────────────────
    st.markdown("<div class='section-header'>Care Coordinator Updates</div>", unsafe_allow_html=True)
    st.caption("Recent outreach and task activity for your panel — last 14 days")

    feed = pd.read_sql_query(
        """SELECT oa.attempt_time, oa.method, oa.outcome, oa.notes,
                  p.first_name || ' ' || p.last_name as patient_name,
                  cc.name as coordinator_name
           FROM outreach_attempts oa
           JOIN patients p ON oa.patient_id = p.patient_id
           JOIN care_coordinators cc ON oa.coordinator_id = cc.coordinator_id
           WHERE p.assigned_provider_id = ?
             AND oa.attempt_time >= date('now','-14 days')
           ORDER BY oa.attempt_time DESC LIMIT 8""",
        conn, params=(prov_id,)
    )
    task_feed = pd.read_sql_query(
        """SELECT ct.completed_at, ct.message_intent, ct.completion_note,
                  p.first_name || ' ' || p.last_name as patient_name,
                  cc.name as coordinator_name
           FROM care_tasks ct
           JOIN patients p ON ct.patient_id = p.patient_id
           JOIN care_coordinators cc ON ct.assigned_coordinator_id = cc.coordinator_id
           WHERE ct.created_by_provider_id = ?
             AND ct.status = 'COMPLETED'
             AND ct.completed_at IS NOT NULL
           ORDER BY ct.completed_at DESC LIMIT 5""",
        conn, params=(prov_id,)
    )

    if feed.empty and task_feed.empty:
        st.info("No coordinator activity in the last 14 days.")
    else:
        for _, r in task_feed.iterrows():
            st.markdown(
                f"<div class='feed-item completed'>✅ <strong>{r['coordinator_name']}</strong> completed task for "
                f"<strong>{r['patient_name']}</strong> — {r['message_intent']}"
                + (f"<br><span style='color:#718096'>{r['completion_note']}</span>" if r['completion_note'] else "")
                + f"<br><span style='font-size:11px;color:#718096'>{fmt_datetime(r['completed_at'])}</span></div>",
                unsafe_allow_html=True,
            )
        for _, r in feed.iterrows():
            icon = "📞" if r["method"] == "call" else "💬" if r["method"] == "text" else "📧"
            cls  = "completed" if r["outcome"] == "reached" else ("warning" if r["outcome"] == "no_answer" else "")
            st.markdown(
                f"<div class='feed-item {cls}'>{icon} <strong>{r['coordinator_name']}</strong> — "
                f"{r['method'].title()} to <strong>{r['patient_name']}</strong>: "
                f"<em>{r['outcome'].replace('_',' ').title()}</em>"
                + (f"<br><span style='color:#718096'>{r['notes']}</span>" if r['notes'] else "")
                + f"<br><span style='font-size:11px;color:#718096'>{fmt_datetime(r['attempt_time'])}</span></div>",
                unsafe_allow_html=True,
            )

    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# VIEW: PATIENT WORKLIST (per-measure drill-down)
# ══════════════════════════════════════════════════════════════════════════════
def view_worklist():
    prov_id = st.session_state.clin_provider
    conn = get_connection()

    measures = pd.read_sql_query(
        "SELECT measure_id, name, description FROM measure_reference ORDER BY priority_weight DESC",
        conn,
    )
    m_options = {row["name"]: row["measure_id"] for _, row in measures.iterrows()}

    st.markdown("<h2 style='margin-bottom:4px'>Patient Worklist</h2>", unsafe_allow_html=True)

    sel_measure_name = st.selectbox("Select Measure", list(m_options.keys()))
    sel_measure_id   = m_options[sel_measure_name]

    desc_row = measures[measures["measure_id"] == sel_measure_id].iloc[0]
    st.info(f"**Measure Definition:** {desc_row['description']}")

    df = pd.read_sql_query(
        """SELECT p.patient_id, p.first_name || ' ' || p.last_name as patient_name,
                  p.age, p.gender, p.medicaid_id,
                  cg.gap_status,
                  pr.risk_bucket, pr.composite_risk,
                  cc.name as coordinator_name
           FROM care_gaps cg
           JOIN patients p ON cg.patient_id = p.patient_id
           LEFT JOIN patient_risk_profile pr ON p.patient_id = pr.patient_id
           LEFT JOIN care_coordinators cc ON p.assigned_coordinator_id = cc.coordinator_id
           WHERE cg.measure_id = ? AND p.assigned_provider_id = ?
           ORDER BY pr.composite_risk DESC NULLS LAST""",
        conn, params=(sel_measure_id, prov_id),
    )
    conn.close()

    if df.empty:
        st.info("No patients in this measure for your panel.")
        return

    open_cnt   = len(df[df["gap_status"] == "OPEN"])
    closed_cnt = len(df[df["gap_status"] == "CLOSED"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Total in Measure", len(df))
    c2.metric("Open Gaps",   open_cnt,   delta=f"{round(open_cnt/max(len(df),1)*100)}% open", delta_color="inverse")
    c3.metric("Closed Gaps", closed_cnt, delta=f"{round(closed_cnt/max(len(df),1)*100)}% closed")

    display = df.copy()
    display["Risk"] = display["risk_bucket"].map(RISK_LABELS)
    display["Score"] = display["composite_risk"].map(lambda x: f"{x:.0f}" if pd.notna(x) else "—")
    display["Status"] = display["gap_status"]

    st.dataframe(
        display[["patient_name", "age", "Status", "Risk", "Score", "coordinator_name"]].rename(
            columns={"patient_name": "Patient", "age": "Age",
                     "coordinator_name": "Care Coordinator"}
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.caption("Click 'Patient Record' in the sidebar and select a patient to view full details.")


# ══════════════════════════════════════════════════════════════════════════════
# VIEW: PATIENT RECORD
# ══════════════════════════════════════════════════════════════════════════════

@st.dialog("Notify Care Coordinator")
def notify_coordinator_dialog(patient_id):
    conn = get_connection()
    p = conn.execute(
        "SELECT first_name, last_name, age, assigned_coordinator_id FROM patients WHERE patient_id=?",
        (patient_id,)
    ).fetchone()
    cc = conn.execute(
        "SELECT name FROM care_coordinators WHERE coordinator_id=?",
        (p["assigned_coordinator_id"],)
    ).fetchone()
    prov_id = st.session_state.clin_provider

    st.markdown(
        f"**Patient:** {p['first_name']} {p['last_name']}, {p['age']}y  &nbsp;|&nbsp; "
        f"**Assigned Coordinator:** {cc['name'] if cc else '—'}"
    )
    st.divider()

    intents = [
        "Schedule dental exam / evaluation",
        "Follow up after ED visit for NTDC",
        "Address overdue periodontal maintenance",
        "Defer routine care",
        "Other care coordination request",
    ]
    intent = st.radio("Message Intent", intents, horizontal=False)
    msg    = st.text_area("Message to Care Coordinator",
                          placeholder="Provide context or specific instructions…", height=120)

    c1, c2 = st.columns(2)
    if c1.button("Send to Care Coordinator", type="primary", use_container_width=True):
        if not msg.strip():
            st.error("Please enter a message.")
        else:
            conn.execute(
                """INSERT INTO care_tasks
                   (patient_id, assigned_coordinator_id, created_by_provider_id,
                    message_intent, message, status, created_at)
                   VALUES (?,?,?,?,?,'OPEN',datetime('now'))""",
                (patient_id, p["assigned_coordinator_id"], prov_id, intent, msg),
            )
            conn.commit()
            conn.close()
            st.success("Task sent!")
            st.rerun()
    if c2.button("Cancel", use_container_width=True):
        conn.close()
        st.rerun()


def view_patient_record():
    prov_id  = st.session_state.clin_provider
    patients = load_provider_patients(prov_id)

    st.markdown("<h2 style='margin-bottom:4px'>Patient Record</h2>", unsafe_allow_html=True)

    # Patient selector
    options  = {f"{r['first_name']} {r['last_name']} ({r['medicaid_id']})": int(r["patient_id"])
                for _, r in patients.iterrows()}
    if not options:
        st.info("No patients on your panel.")
        return

    default_label = next(
        (lbl for lbl, pid in options.items() if pid == st.session_state.clin_patient), None
    ) or list(options.keys())[0]

    selected_label = st.selectbox("Select Patient", list(options.keys()), index=list(options.keys()).index(default_label))
    patient_id = options[selected_label]
    st.session_state.clin_patient = patient_id

    conn = get_connection()
    p    = conn.execute(
        """SELECT p.*, pr.composite_risk, pr.risk_bucket, pr.engagement_score,
                  pr.clinical_score, pr.sdoh_score,
                  prov.name as provider_name, cc.name as coordinator_name
           FROM patients p
           LEFT JOIN patient_risk_profile pr ON p.patient_id = pr.patient_id
           LEFT JOIN providers prov ON p.assigned_provider_id = prov.provider_id
           LEFT JOIN care_coordinators cc ON p.assigned_coordinator_id = cc.coordinator_id
           WHERE p.patient_id=?""", (patient_id,)
    ).fetchone()

    # ── Header ────────────────────────────────────────────────────────────────
    hc1, hc2, hc3 = st.columns([3, 1.5, 1.5])
    with hc1:
        bucket = p["risk_bucket"] or "LOW"
        st.markdown(
            f"<h3 style='margin:0'>{p['first_name']} {p['last_name']}</h3>"
            f"<span style='color:#718096'>{p['age']}y · {p['gender']} · Medicaid ID: {p['medicaid_id']}</span><br>"
            f"<span style='color:#718096'>Provider: {p['provider_name']} &nbsp;|&nbsp; Coordinator: {p['coordinator_name']}</span>",
            unsafe_allow_html=True,
        )
    with hc2:
        score = p["composite_risk"] or 0
        color = RISK_COLORS.get(bucket, "#718096")
        st.markdown(
            f"<div style='text-align:center;background:{color}15;border:1px solid {color}40;"
            f"border-radius:8px;padding:10px'>"
            f"<div style='font-size:28px;font-weight:800;color:{color}'>{score:.0f}</div>"
            f"<div style='font-size:12px;color:{color};font-weight:600'>{RISK_LABELS.get(bucket,'—')} Risk</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    with hc3:
        if st.button("📢 Notify Care Coordinator", type="primary", use_container_width=True):
            notify_coordinator_dialog(patient_id)

    st.divider()

    left, right = st.columns([3, 2])

    # ── Care Gaps ─────────────────────────────────────────────────────────────
    with left:
        st.markdown("<div class='section-header'>Dental Care Gaps (Open)</div>", unsafe_allow_html=True)
        gaps = pd.read_sql_query(
            """SELECT cg.gap_id, cg.gap_status, cg.last_evaluated_at,
                      cg.closed_at, cg.closure_note,
                      mr.name, mr.description, mr.category, mr.priority_weight
               FROM care_gaps cg
               JOIN measure_reference mr ON cg.measure_id = mr.measure_id
               WHERE cg.patient_id = ?
               ORDER BY cg.gap_status, mr.priority_weight DESC""",
            conn, params=(patient_id,)
        )
        open_gaps = gaps[gaps["gap_status"] == "OPEN"]
        if open_gaps.empty:
            st.success("No open care gaps for this patient.")
        else:
            for _, g in open_gaps.iterrows():
                with st.expander(f"⚠️  {g['name']}  ·  {g['category']}"):
                    st.markdown(f"*{g['description']}*")
                    st.caption(f"Last evaluated: {fmt_date(g['last_evaluated_at'])}")
                    close_note = st.text_input("Closure note", key=f"close_note_{g['gap_id']}", placeholder="Reason for closing…")
                    if st.button("Mark Closed", key=f"close_{g['gap_id']}"):
                        conn.execute(
                            "UPDATE care_gaps SET gap_status='CLOSED', closed_at=datetime('now'), "
                            "closed_by=?, closure_note=? WHERE gap_id=?",
                            (p["provider_name"], close_note, g["gap_id"]),
                        )
                        conn.commit()
                        from utils.calculations import update_risk_profile
                        update_risk_profile(patient_id, conn)
                        st.success("Gap closed.")
                        st.rerun()

        closed_gaps = gaps[gaps["gap_status"] == "CLOSED"]
        if not closed_gaps.empty:
            with st.expander(f"✅ Closed gaps ({len(closed_gaps)})"):
                for _, g in closed_gaps.iterrows():
                    st.markdown(f"**{g['name']}** — closed {fmt_date(g['closed_at'])}")

        # Diagnoses
        st.markdown("<div class='section-header' style='margin-top:20px'>Active Diagnoses</div>", unsafe_allow_html=True)
        diags = pd.read_sql_query(
            "SELECT icd_code, description FROM diagnoses WHERE patient_id=? AND is_active=1",
            conn, params=(patient_id,)
        )
        if diags.empty:
            st.caption("No active diagnoses on record.")
        else:
            for _, d in diags.iterrows():
                st.markdown(f"• **{d['icd_code']}** — {d['description']}")

    # ── SDOH + Outreach ───────────────────────────────────────────────────────
    with right:
        st.markdown("<div class='section-header'>SDOH Assessment</div>", unsafe_allow_html=True)
        sdoh = conn.execute(
            "SELECT * FROM sdoh_assessment WHERE patient_id=?", (patient_id,)
        ).fetchone()
        if sdoh:
            flags = {
                "Transportation": sdoh["transportation"],
                "Communication Challenges": sdoh["communication_challenges"],
                "Cost / Financial Anxiety": sdoh["cost_anxiety"],
                "Dental Fear": sdoh["dental_fear"],
                "Work Schedule Constraints": sdoh["work_schedule_constraints"],
            }
            any_flag = False
            for label, val in flags.items():
                if val:
                    st.markdown(f"🔴 **{label}**")
                    any_flag = True
            if not any_flag:
                st.success("No SDOH barriers identified.")
            st.caption(f"ADI Decile: **{p['adi_decile']}**/10 &nbsp;·&nbsp; Assessed {fmt_date(sdoh['assessed_at'])}")
        else:
            st.caption("No SDOH assessment on file.")

        st.markdown("<div class='section-header' style='margin-top:20px'>Recent Outreach</div>", unsafe_allow_html=True)
        outreach = pd.read_sql_query(
            """SELECT oa.method, oa.outcome, oa.notes, oa.attempt_time,
                      cc.name as coordinator
               FROM outreach_attempts oa
               JOIN care_coordinators cc ON oa.coordinator_id = cc.coordinator_id
               WHERE oa.patient_id = ?
               ORDER BY oa.attempt_time DESC LIMIT 6""",
            conn, params=(patient_id,)
        )
        if outreach.empty:
            st.caption("No outreach recorded.")
        else:
            for _, o in outreach.iterrows():
                icon = "📞" if o["method"] == "call" else "💬" if o["method"] == "text" else "📧"
                color = "#38A169" if o["outcome"] == "reached" else "#718096"
                st.markdown(
                    f"{icon} **{o['method'].title()}** → "
                    f"<span style='color:{color}'>{o['outcome'].replace('_',' ').title()}</span> &nbsp;"
                    f"<span style='font-size:11px;color:#A0AEC0'>{fmt_datetime(o['attempt_time'])}</span>"
                    + (f"<br><span style='font-size:12px;color:#718096'>{o['notes']}</span>" if o['notes'] else ""),
                    unsafe_allow_html=True,
                )

        st.markdown("<div class='section-header' style='margin-top:20px'>Open Tasks</div>", unsafe_allow_html=True)
        tasks = pd.read_sql_query(
            """SELECT ct.task_id, ct.message_intent, ct.message, ct.status, ct.created_at,
                      cc.name as coordinator
               FROM care_tasks ct
               JOIN care_coordinators cc ON ct.assigned_coordinator_id = cc.coordinator_id
               WHERE ct.patient_id=? AND ct.status != 'COMPLETED'
               ORDER BY ct.created_at DESC""",
            conn, params=(patient_id,)
        )
        if tasks.empty:
            st.caption("No open tasks.")
        else:
            for _, t in tasks.iterrows():
                st.markdown(
                    f"📋 **{t['message_intent']}** → {t['coordinator']}<br>"
                    f"<span style='font-size:12px;color:#718096'>{t['message']}</span><br>"
                    f"<span style='font-size:11px;color:#A0AEC0'>Created {fmt_datetime(t['created_at'])}</span>",
                    unsafe_allow_html=True,
                )

    conn.close()


# ── Route to correct view ─────────────────────────────────────────────────────
if st.session_state.clin_view == "Patient Panel":
    view_patient_panel()
elif st.session_state.clin_view == "Patient Worklist":
    view_worklist()
else:
    view_patient_record()
