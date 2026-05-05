from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import pandas as pd

from db.schema import get_connection
from utils.calculations import update_risk_profile

router = APIRouter(tags=["coordinator"])


class LogOutreachBody(BaseModel):
    patient_id: int
    coordinator_id: int
    method: str
    outcome: str
    notes: Optional[str] = None
    care_gap_id: Optional[int] = None


@router.get("/{coordinator_id}/patients")
def coordinator_patients(coordinator_id: int):
    conn = get_connection()
    rows = pd.read_sql_query(
        """SELECT p.patient_id, p.first_name, p.last_name, p.age, p.gender,
                  p.medicaid_id, p.adi_decile, p.is_diabetic,
                  pr.composite_risk, pr.risk_bucket,
                  pr.engagement_score, pr.clinical_score, pr.sdoh_score,
                  prov.name as provider_name
           FROM patients p
           LEFT JOIN patient_risk_profile pr ON p.patient_id=pr.patient_id
           LEFT JOIN providers prov ON p.assigned_provider_id=prov.provider_id
           WHERE p.assigned_coordinator_id=? AND p.is_active=1
           ORDER BY pr.composite_risk DESC NULLS LAST""",
        conn, params=(coordinator_id,),
    )

    # Attach last contact date + open gap count per patient
    result = []
    for _, row in rows.iterrows():
        last = conn.execute(
            "SELECT attempt_time FROM outreach_attempts WHERE patient_id=? ORDER BY attempt_time DESC LIMIT 1",
            (row["patient_id"],),
        ).fetchone()
        open_gaps = conn.execute(
            "SELECT COUNT(*) FROM care_gaps WHERE patient_id=? AND gap_status='OPEN'",
            (row["patient_id"],),
        ).fetchone()[0]
        d = dict(row)
        d["last_contact"] = last[0] if last else None
        d["open_gap_count"] = open_gaps
        result.append(d)

    # KPI summary
    total     = len(result)
    high_risk = sum(1 for r in result if r.get("risk_bucket") in ("HIGH", "VERY_HIGH"))
    open_tasks = conn.execute(
        "SELECT COUNT(*) FROM care_tasks WHERE assigned_coordinator_id=? AND status='OPEN'",
        (coordinator_id,)
    ).fetchone()[0]
    outreach_wk = conn.execute(
        "SELECT COUNT(*) FROM outreach_attempts WHERE coordinator_id=? AND attempt_time >= date('now','-7 days')",
        (coordinator_id,)
    ).fetchone()[0]

    conn.close()
    return {
        "kpis": {
            "total": total,
            "high_risk": high_risk,
            "open_tasks": open_tasks,
            "outreach_this_week": outreach_wk,
        },
        "patients": result,
    }


@router.post("/outreach")
def log_outreach(body: LogOutreachBody):
    conn = get_connection()
    conn.execute(
        """INSERT INTO outreach_attempts
           (patient_id, coordinator_id, method, outcome, notes, care_gap_id, attempt_time)
           VALUES (?,?,?,?,?,?,datetime('now'))""",
        (body.patient_id, body.coordinator_id, body.method,
         body.outcome, body.notes, body.care_gap_id),
    )
    # Positive outcomes → engagement event
    etype = None
    if body.outcome == "reached":
        etype = "call_answered"
    elif body.outcome == "scheduled":
        etype = "appt_scheduled"
    if etype:
        conn.execute(
            """INSERT INTO engagement_events
               (patient_id, coordinator_id, event_type, outcome, event_timestamp)
               VALUES (?,?,?,?,datetime('now'))""",
            (body.patient_id, body.coordinator_id, etype, "positive"),
        )
    conn.commit()
    update_risk_profile(body.patient_id, conn)
    conn.commit()
    conn.close()
    return {"ok": True}
