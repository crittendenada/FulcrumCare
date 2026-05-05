from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
import pandas as pd

from db.schema import get_connection

router = APIRouter(tags=["clinician"])


class CreateTaskBody(BaseModel):
    patient_id: int
    coordinator_id: int
    provider_id: int
    intent: str
    message: str


@router.get("/{provider_id}/panel")
def clinician_panel(provider_id: int):
    conn = get_connection()

    # KPIs
    measures_kpi = []
    for mid, mname in [
        ("PREV_DENTAL_12M",   "Preventive Dental Visit"),
        ("ORAL_EVAL_DIABETES","Oral Eval – Adults w/ Diabetes"),
        ("PERIODONTAL_EVAL",  "Periodontal Evaluation"),
    ]:
        cnt = conn.execute(
            """SELECT COUNT(*) FROM care_gaps cg
               JOIN patients p ON cg.patient_id=p.patient_id
               WHERE cg.measure_id=? AND cg.gap_status='OPEN'
                 AND p.assigned_provider_id=?""",
            (mid, provider_id),
        ).fetchone()[0]
        measures_kpi.append({"measure_id": mid, "name": mname, "open_count": cnt})

    # Population stats
    total = conn.execute(
        "SELECT COUNT(*) FROM patients WHERE assigned_provider_id=? AND is_active=1",
        (provider_id,)
    ).fetchone()[0]
    open_gap_patients = conn.execute(
        """SELECT COUNT(DISTINCT cg.patient_id) FROM care_gaps cg
           JOIN patients p ON cg.patient_id=p.patient_id
           WHERE cg.gap_status='OPEN' AND p.assigned_provider_id=?""",
        (provider_id,)
    ).fetchone()[0]
    high_risk = conn.execute(
        """SELECT COUNT(*) FROM patient_risk_profile pr
           JOIN patients p ON pr.patient_id=p.patient_id
           WHERE pr.risk_bucket IN ('HIGH','VERY_HIGH')
             AND p.assigned_provider_id=?""",
        (provider_id,)
    ).fetchone()[0]
    ed_visits = conn.execute(
        """SELECT COUNT(*) FROM encounters e
           JOIN patients p ON e.patient_id=p.patient_id
           WHERE e.encounter_type='ED'
             AND p.assigned_provider_id=?
             AND e.encounter_date >= date('now','-365 days')""",
        (provider_id,)
    ).fetchone()[0]

    # Priority patients (HIGH + VERY_HIGH, ordered by score)
    priority = pd.read_sql_query(
        """SELECT p.patient_id, p.first_name, p.last_name, p.age, p.gender,
                  p.medicaid_id, pr.composite_risk, pr.risk_bucket,
                  cc.name as coordinator_name
           FROM patients p
           JOIN patient_risk_profile pr ON p.patient_id=pr.patient_id
           LEFT JOIN care_coordinators cc ON p.assigned_coordinator_id=cc.coordinator_id
           WHERE p.assigned_provider_id=? AND p.is_active=1
             AND pr.risk_bucket IN ('HIGH','VERY_HIGH')
           ORDER BY pr.composite_risk DESC LIMIT 12""",
        conn, params=(provider_id,),
    )

    # Attach top open gap for each priority patient
    priority_list = []
    for _, row in priority.iterrows():
        gap_row = conn.execute(
            """SELECT mr.name FROM care_gaps cg
               JOIN measure_reference mr ON cg.measure_id=mr.measure_id
               WHERE cg.patient_id=? AND cg.gap_status='OPEN'
               ORDER BY mr.priority_weight DESC LIMIT 1""",
            (row["patient_id"],),
        ).fetchone()
        has_appt = conn.execute(
            "SELECT 1 FROM engagement_events WHERE patient_id=? AND event_type='appt_scheduled' LIMIT 1",
            (row["patient_id"],),
        ).fetchone()
        d = dict(row)
        d["top_gap"] = gap_row[0] if gap_row else None
        d["appt_scheduled"] = bool(has_appt)
        priority_list.append(d)

    # Coordinator feed (last 14 days)
    outreach_feed = pd.read_sql_query(
        """SELECT oa.attempt_time, oa.method, oa.outcome, oa.notes,
                  p.first_name || ' ' || p.last_name as patient_name,
                  p.patient_id,
                  cc.name as coordinator_name
           FROM outreach_attempts oa
           JOIN patients p ON oa.patient_id=p.patient_id
           JOIN care_coordinators cc ON oa.coordinator_id=cc.coordinator_id
           WHERE p.assigned_provider_id=?
             AND oa.attempt_time >= date('now','-14 days')
           ORDER BY oa.attempt_time DESC LIMIT 6""",
        conn, params=(provider_id,),
    ).to_dict(orient="records")

    task_feed = pd.read_sql_query(
        """SELECT ct.completed_at, ct.message_intent, ct.completion_note,
                  p.first_name || ' ' || p.last_name as patient_name,
                  p.patient_id,
                  cc.name as coordinator_name
           FROM care_tasks ct
           JOIN patients p ON ct.patient_id=p.patient_id
           JOIN care_coordinators cc ON ct.assigned_coordinator_id=cc.coordinator_id
           WHERE ct.created_by_provider_id=? AND ct.status='COMPLETED'
             AND ct.completed_at IS NOT NULL
           ORDER BY ct.completed_at DESC LIMIT 5""",
        conn, params=(provider_id,),
    ).to_dict(orient="records")

    conn.close()
    return {
        "measures_kpi": measures_kpi,
        "stats": {
            "total": total,
            "open_gap_patients": open_gap_patients,
            "high_risk": high_risk,
            "ed_visits": ed_visits,
        },
        "priority_patients": priority_list,
        "outreach_feed": outreach_feed,
        "task_feed": task_feed,
    }


@router.get("/{provider_id}/worklist")
def clinician_worklist(provider_id: int, measure_id: str = Query(...)):
    conn = get_connection()
    rows = pd.read_sql_query(
        """SELECT p.patient_id, p.first_name || ' ' || p.last_name as patient_name,
                  p.age, p.gender, p.medicaid_id,
                  cg.gap_status,
                  pr.risk_bucket, pr.composite_risk,
                  cc.name as coordinator_name
           FROM care_gaps cg
           JOIN patients p ON cg.patient_id=p.patient_id
           LEFT JOIN patient_risk_profile pr ON p.patient_id=pr.patient_id
           LEFT JOIN care_coordinators cc ON p.assigned_coordinator_id=cc.coordinator_id
           WHERE cg.measure_id=? AND p.assigned_provider_id=?
           ORDER BY pr.composite_risk DESC NULLS LAST""",
        conn, params=(measure_id, provider_id),
    ).to_dict(orient="records")
    conn.close()
    return rows


@router.post("/tasks")
def create_task(body: CreateTaskBody):
    conn = get_connection()
    conn.execute(
        """INSERT INTO care_tasks
           (patient_id, assigned_coordinator_id, created_by_provider_id,
            message_intent, message, status, created_at)
           VALUES (?,?,?,?,?,'OPEN',datetime('now'))""",
        (body.patient_id, body.coordinator_id, body.provider_id, body.intent, body.message),
    )
    conn.commit()
    conn.close()
    return {"ok": True}
