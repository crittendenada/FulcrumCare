import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st
import pandas as pd

from utils.helpers import (
    apply_css, ensure_seeded, get_connection,
    risk_badge, risk_color, RISK_COLORS, RISK_LABELS, fmt_date, fmt_datetime,
)
from utils.calculations import update_risk_profile

st.set_page_config(page_title="Care Coordinator – FulcrumCare", page_icon="👥", layout="wide")
apply_css()
ensure_seeded()

# ── Session state defaults ────────────────────────────────────────────────────
if "cc_view"       not in st.session_state: st.session_state.cc_view = "My Patients"
if "cc_patient"    not in st.session_state: st.session_state.cc_patient = None
if "cc_coord"      not in st.session_state: st.session_state.cc_coord = 1

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='font-size:18px;font-weight:800;color:#2B6CB0'>🦷 FulcrumCare</div>"
        "<div style='font-size:11px;color:#718096'>Care Coordinator Portal</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    conn = get_connection()
    coordinators = pd.read_sql_query("SELECT coordinator_id, name FROM care_coordinators", conn)
    conn.close()

    coord_options = {r["name"]: r["coordinator_id"] for _, r in coordinators.iterrows()}
    sel_coord_name = st.selectbox("Viewing as", list(coord_options.keys()))
    st.session_state.cc_coord = coord_options[sel_coord_name]

    st.divider()
    view = st.radio(
        "Navigation",
        ["My Patients", "Patient Workup"],
        index=["My Patients", "Patient Workup"].index(st.session_state.cc_view),
    )
    st.session_state.cc_view = view


# ── Shared patient list ───────────────────────────────────────────────────────
@st.cache_data(ttl=0)
def load_coord_patients(coord_id):
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT p.patient_id, p.first_name, p.last_name, p.age, p.gender,
                  p.medicaid_id, p.is_diabetic, p.adi_decile,
                  pr.composite_risk, pr.risk_bucket,
                  pr.engagement_score, pr.clinical_score, pr.sdoh_score,
                  prov.name as provider_name
           FROM patients p
           LEFT JOIN patient_risk_profile pr ON p.patient_id = pr.patient_id
           LEFT JOIN providers prov ON p.assigned_provider_id = prov.provider_id
           WHERE p.assigned_coordinator_id = ? AND p.is_active = 1
           ORDER BY pr.composite_risk DESC NULLS LAST""",
        conn, params=(coord_id,)
    )
    conn.close()
    return df


# ══════════════════════════════════════════════════════════════════════════════
# VIEW: MY PATIENTS
# ══════════════════════════════════════════════════════════════════════════════
def view_my_patients():
    coord_id = st.session_state.cc_coord
    patients = load_coord_patients(coord_id)

    st.markdown(
        "<h2 style='margin-bottom:2px'>My Patients</h2>"
        "<p style='color:#718096;margin-top:0'>Manage outreach and engagement for your assigned population.</p>",
        unsafe_allow_html=True,
    )

    conn = get_connection()

    # KPIs
    total     = len(patients)
    high_risk = len(patients[patients["risk_bucket"].isin(["HIGH", "VERY_HIGH"])])
    open_tasks = conn.execute(
        """SELECT COUNT(*) FROM care_tasks
           WHERE assigned_coordinator_id=? AND status='OPEN'""", (coord_id,)
    ).fetchone()[0]
    outreach_wk = conn.execute(
        """SELECT COUNT(*) FROM outreach_attempts
           WHERE coordinator_id=? AND attempt_time >= date('now','-7 days')""", (coord_id,)
    ).fetchone()[0]
    conn.close()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Assigned Patients",  total)
    m2.metric("High / Very High Risk", high_risk,
              delta=f"{round(high_risk/max(total,1)*100)}% of panel", delta_color="inverse")
    m3.metric("Open Tasks",         open_tasks)
    m4.metric("Outreach This Week", outreach_wk)

    st.divider()

    # Filter
    filt_col, _, _ = st.columns([2, 2, 2])
    with filt_col:
        risk_filter = st.selectbox("Filter by Risk",
                                   ["All", "Very High", "High", "Moderate", "Low"])

    rev_labels = {"Very High": "VERY_HIGH", "High": "HIGH", "Moderate": "MEDIUM", "Low": "LOW"}
    display = patients.copy()
    if risk_filter != "All":
        display = display[display["risk_bucket"] == rev_labels[risk_filter]]

    st.markdown(f"**{len(display)} patients**", unsafe_allow_html=True)
    st.markdown("<hr style='margin:4px 0'>", unsafe_allow_html=True)

    for _, row in display.iterrows():
        c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 2, 1])
        bucket = row["risk_bucket"] or "LOW"
        score  = row["composite_risk"] or 0
        color  = RISK_COLORS.get(bucket, "#718096")

        with c1:
            st.markdown(
                f"**{row['first_name']} {row['last_name']}** "
                f"<span style='font-size:12px;color:#718096'>{row['age']}{'M' if row['gender']=='M' else 'F'}</span>",
                unsafe_allow_html=True,
            )
            st.caption(row["provider_name"])
        c2.markdown(risk_badge(bucket), unsafe_allow_html=True)
        c3.markdown(
            f"<span style='font-size:18px;font-weight:700;color:{color}'>{score:.0f}</span>",
            unsafe_allow_html=True,
        )
        with c4:
            # Last contact
            conn = get_connection()
            last = conn.execute(
                "SELECT attempt_time FROM outreach_attempts WHERE patient_id=? ORDER BY attempt_time DESC LIMIT 1",
                (row["patient_id"],)
            ).fetchone()
            conn.close()
            st.caption(f"Last contact: {fmt_date(last[0]) if last else 'Never'}")
        with c5:
            if st.button("Workup", key=f"wu_{row['patient_id']}"):
                st.session_state.cc_patient = int(row["patient_id"])
                st.session_state.cc_view    = "Patient Workup"
                st.rerun()

        st.markdown("<hr style='margin:2px 0;border-color:#EDF2F7'>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# VIEW: PATIENT WORKUP
# ══════════════════════════════════════════════════════════════════════════════
def view_patient_workup():
    coord_id = st.session_state.cc_coord
    patients  = load_coord_patients(coord_id)

    st.markdown("<h2 style='margin-bottom:4px'>Patient Workup</h2>", unsafe_allow_html=True)

    options = {
        f"{r['first_name']} {r['last_name']} ({r['medicaid_id']})": int(r["patient_id"])
        for _, r in patients.iterrows()
    }
    if not options:
        st.info("No patients assigned to you.")
        return

    default_lbl = next(
        (lbl for lbl, pid in options.items() if pid == st.session_state.cc_patient), None
    ) or list(options.keys())[0]

    selected_lbl = st.selectbox("Select Patient", list(options.keys()),
                                index=list(options.keys()).index(default_lbl))
    patient_id = options[selected_lbl]
    st.session_state.cc_patient = patient_id

    conn = get_connection()
    p = conn.execute(
        """SELECT p.*, pr.composite_risk, pr.risk_bucket,
                  pr.engagement_score, pr.clinical_score, pr.sdoh_score,
                  prov.name as provider_name
           FROM patients p
           LEFT JOIN patient_risk_profile pr ON p.patient_id = pr.patient_id
           LEFT JOIN providers prov ON p.assigned_provider_id = prov.provider_id
           WHERE p.patient_id=?""", (patient_id,)
    ).fetchone()

    # ── Patient header ────────────────────────────────────────────────────────
    bucket = p["risk_bucket"] or "LOW"
    color  = RISK_COLORS.get(bucket, "#718096")
    score  = p["composite_risk"] or 0

    hc1, hc2 = st.columns([4, 1.5])
    with hc1:
        st.markdown(
            f"<h3 style='margin:0'>{p['first_name']} {p['last_name']}</h3>"
            f"<span style='color:#718096'>{p['age']}y · {p['gender']} · Medicaid ID: {p['medicaid_id']}</span><br>"
            f"<span style='color:#718096'>Provider: {p['provider_name']} &nbsp;|&nbsp; "
            f"ADI Decile: {p['adi_decile']}/10</span>",
            unsafe_allow_html=True,
        )
    with hc2:
        st.markdown(
            f"<div style='text-align:center;background:{color}15;border:2px solid {color};"
            f"border-radius:10px;padding:12px'>"
            f"<div style='font-size:36px;font-weight:900;color:{color}'>{score:.0f}</div>"
            f"<div style='font-size:13px;font-weight:700;color:{color}'>{RISK_LABELS.get(bucket,'—')} Risk</div>"
            f"<div style='font-size:10px;color:#A0AEC0;margin-top:4px'>"
            f"E:{p['engagement_score']:.0f} C:{p['clinical_score']:.0f} S:{p['sdoh_score']:.0f}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    st.divider()

    left, right = st.columns([3, 2])

    # ── Left: care gaps + tasks ───────────────────────────────────────────────
    with left:
        # Pending tasks from clinicians
        tasks = pd.read_sql_query(
            """SELECT ct.task_id, ct.message_intent, ct.message, ct.status, ct.created_at,
                      prov.name as provider_name
               FROM care_tasks ct
               JOIN providers prov ON ct.created_by_provider_id = prov.provider_id
               WHERE ct.patient_id=? AND ct.assigned_coordinator_id=?
                 AND ct.status != 'COMPLETED'
               ORDER BY ct.created_at DESC""",
            conn, params=(patient_id, coord_id),
        )

        if not tasks.empty:
            st.markdown("<div class='section-header'>📋 Tasks from Clinician</div>", unsafe_allow_html=True)
            for _, t in tasks.iterrows():
                with st.expander(f"**{t['message_intent']}** — from {t['provider_name']} · {fmt_date(t['created_at'])}"):
                    st.markdown(t["message"])
                    note = st.text_input("Completion note", key=f"tnote_{t['task_id']}", placeholder="What was done?")
                    if st.button("✅ Mark Complete", key=f"tcomplete_{t['task_id']}", type="primary"):
                        conn.execute(
                            """UPDATE care_tasks SET status='COMPLETED',
                               completed_at=datetime('now'), completion_note=?
                               WHERE task_id=?""",
                            (note, t["task_id"]),
                        )
                        conn.commit()
                        st.success("Task marked complete.")
                        st.rerun()

        # Open care gaps
        st.markdown("<div class='section-header' style='margin-top:16px'>Open Care Gaps</div>", unsafe_allow_html=True)
        gaps = pd.read_sql_query(
            """SELECT cg.gap_id, cg.gap_status, cg.last_evaluated_at,
                      mr.name, mr.description, mr.category
               FROM care_gaps cg
               JOIN measure_reference mr ON cg.measure_id = mr.measure_id
               WHERE cg.patient_id=? AND cg.gap_status='OPEN'
               ORDER BY mr.priority_weight DESC""",
            conn, params=(patient_id,)
        )
        if gaps.empty:
            st.success("No open care gaps.")
        else:
            for _, g in gaps.iterrows():
                st.markdown(
                    f"⚠️ **{g['name']}** &nbsp;"
                    f"<span style='font-size:12px;color:#718096'>{g['category']}</span><br>"
                    f"<span style='font-size:12px;color:#4A5568'>{g['description']}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown("<hr style='margin:6px 0;border-color:#EDF2F7'>", unsafe_allow_html=True)

    # ── Right: log outreach + activity log ───────────────────────────────────
    with right:
        st.markdown("<div class='section-header'>Log Outreach Attempt</div>", unsafe_allow_html=True)
        with st.form("log_outreach", clear_on_submit=True):
            method = st.selectbox("Method", ["call", "text", "email", "in-person"])
            outcome = st.selectbox("Outcome", ["reached", "voicemail", "no_answer", "refused", "scheduled"])
            notes = st.text_area("Notes", placeholder="What happened? Any follow-up needed?", height=80)
            gap_opts = {f"{g['name']}": g["gap_id"] for _, g in gaps.iterrows()} if not gaps.empty else {}
            gap_opts = {"(General / No specific gap)": None} | gap_opts
            related_gap = st.selectbox("Related Care Gap", list(gap_opts.keys()))
            submitted = st.form_submit_button("Log Outreach", type="primary", use_container_width=True)

            if submitted:
                gap_id = gap_opts[related_gap]
                conn.execute(
                    """INSERT INTO outreach_attempts
                       (patient_id, coordinator_id, method, outcome, notes, care_gap_id, attempt_time)
                       VALUES (?,?,?,?,?,?,datetime('now'))""",
                    (patient_id, coord_id, method, outcome, notes, gap_id),
                )
                # Log engagement event for positive outcomes
                etype = None
                if outcome == "reached":
                    etype = "call_answered"
                elif outcome == "scheduled":
                    etype = "appt_scheduled"
                if etype:
                    conn.execute(
                        """INSERT INTO engagement_events
                           (patient_id, coordinator_id, event_type, outcome, event_timestamp)
                           VALUES (?,?,?,?,datetime('now'))""",
                        (patient_id, coord_id, etype, "positive"),
                    )
                conn.commit()
                update_risk_profile(patient_id, conn)
                st.success("Outreach logged and risk score updated.")
                st.rerun()

        # SDOH flags
        st.markdown("<div class='section-header' style='margin-top:16px'>SDOH Barriers</div>", unsafe_allow_html=True)
        sdoh = conn.execute(
            "SELECT * FROM sdoh_assessment WHERE patient_id=?", (patient_id,)
        ).fetchone()
        if sdoh:
            flags = {
                "Transportation": sdoh["transportation"],
                "Communication": sdoh["communication_challenges"],
                "Cost / Financial": sdoh["cost_anxiety"],
                "Dental Fear": sdoh["dental_fear"],
                "Work Schedule": sdoh["work_schedule_constraints"],
            }
            active = [k for k, v in flags.items() if v]
            if active:
                for f in active:
                    st.markdown(f"🔴 {f}")
            else:
                st.caption("No barriers flagged.")
        else:
            st.caption("No SDOH assessment on file.")

        # Activity timeline
        st.markdown("<div class='section-header' style='margin-top:16px'>Activity Timeline</div>", unsafe_allow_html=True)
        activity = pd.read_sql_query(
            """SELECT attempt_time as ts, method || ' → ' || outcome as event, notes
               FROM outreach_attempts WHERE patient_id=?
               UNION ALL
               SELECT event_timestamp as ts, event_type as event, outcome as notes
               FROM engagement_events WHERE patient_id=?
               ORDER BY ts DESC LIMIT 10""",
            conn, params=(patient_id, patient_id),
        )
        if activity.empty:
            st.caption("No activity yet.")
        else:
            for _, a in activity.iterrows():
                st.markdown(
                    f"<span style='font-size:12px'><strong>{a['event'].replace('_',' ').title()}</strong> "
                    f"<span style='color:#A0AEC0'>{fmt_datetime(a['ts'])}</span>"
                    + (f"<br><span style='color:#718096'>{a['notes']}</span>" if a["notes"] else "")
                    + "</span>",
                    unsafe_allow_html=True,
                )
                st.markdown("<hr style='margin:4px 0;border-color:#EDF2F7'>", unsafe_allow_html=True)

    conn.close()


# ── Route ─────────────────────────────────────────────────────────────────────
if st.session_state.cc_view == "My Patients":
    view_my_patients()
else:
    view_patient_workup()
