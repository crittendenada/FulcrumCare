from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import pandas as pd

from db.schema import get_connection
from utils.calculations import update_risk_profile

router = APIRouter(tags=["patients"])


# ── Response models ───────────────────────────────────────────────────────────

class CloseGapBody(BaseModel):
    closed_by: str
    closure_note: Optional[str] = None

class CompleteTaskBody(BaseModel):
    completion_note: Optional[str] = None


# ── Lookups ───────────────────────────────────────────────────────────────────

@router.get("/providers")
def list_providers():
    conn = get_connection()
    rows = pd.read_sql_query(
        "SELECT p.provider_id, p.name, p.specialty, c.name as clinic_name, p.clinic_id "
        "FROM providers p JOIN clinics c ON p.clinic_id = c.clinic_id",
        conn,
    ).to_dict(orient="records")
    conn.close()
    return rows


@router.get("/coordinators")
def list_coordinators():
    conn = get_connection()
    rows = pd.read_sql_query(
        "SELECT coordinator_id, name, email FROM care_coordinators", conn
    ).to_dict(orient="records")
    conn.close()
    return rows


@router.get("/measures")
def list_measures():
    conn = get_connection()
    rows = pd.read_sql_query(
        "SELECT measure_id, name, description, category, priority_weight FROM measure_reference "
        "ORDER BY priority_weight DESC",
        conn,
    ).to_dict(orient="records")
    conn.close()
    return rows


# ── Patient detail ────────────────────────────────────────────────────────────

@router.get("/patients/{patient_id}")
def get_patient(patient_id: int):
    conn = get_connection()
    row = conn.execute(
        """SELECT p.*, pr.composite_risk, pr.risk_bucket,
                  pr.engagement_score, pr.clinical_score, pr.sdoh_score,
                  prov.name as provider_name,
                  cc.name as coordinator_name, cc.coordinator_id
           FROM patients p
           LEFT JOIN patient_risk_profile pr ON p.patient_id = pr.patient_id
           LEFT JOIN providers prov ON p.assigned_provider_id = prov.provider_id
           LEFT JOIN care_coordinators cc ON p.assigned_coordinator_id = cc.coordinator_id
           WHERE p.patient_id = ?""",
        (patient_id,),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")
    return dict(row)


@router.get("/patients/{patient_id}/gaps")
def get_patient_gaps(patient_id: int):
    conn = get_connection()
    rows = pd.read_sql_query(
        """SELECT cg.gap_id, cg.gap_status, cg.last_evaluated_at,
                  cg.closed_at, cg.closed_by, cg.closure_note,
                  mr.measure_id, mr.name, mr.description, mr.category, mr.priority_weight
           FROM care_gaps cg
           JOIN measure_reference mr ON cg.measure_id = mr.measure_id
           WHERE cg.patient_id = ?
           ORDER BY cg.gap_status, mr.priority_weight DESC""",
        conn, params=(patient_id,),
    ).to_dict(orient="records")
    conn.close()
    return rows


@router.get("/patients/{patient_id}/outreach")
def get_patient_outreach(patient_id: int):
    conn = get_connection()
    rows = pd.read_sql_query(
        """SELECT oa.attempt_id, oa.method, oa.outcome, oa.notes, oa.attempt_time,
                  cc.name as coordinator_name
           FROM outreach_attempts oa
           JOIN care_coordinators cc ON oa.coordinator_id = cc.coordinator_id
           WHERE oa.patient_id = ?
           ORDER BY oa.attempt_time DESC LIMIT 15""",
        conn, params=(patient_id,),
    ).to_dict(orient="records")
    conn.close()
    return rows


@router.get("/patients/{patient_id}/tasks")
def get_patient_tasks(patient_id: int):
    conn = get_connection()
    rows = pd.read_sql_query(
        """SELECT ct.task_id, ct.message_intent, ct.message, ct.status,
                  ct.created_at, ct.completed_at, ct.completion_note,
                  cc.name as coordinator_name,
                  prov.name as provider_name
           FROM care_tasks ct
           LEFT JOIN care_coordinators cc ON ct.assigned_coordinator_id = cc.coordinator_id
           LEFT JOIN providers prov ON ct.created_by_provider_id = prov.provider_id
           WHERE ct.patient_id = ?
           ORDER BY ct.created_at DESC""",
        conn, params=(patient_id,),
    ).to_dict(orient="records")
    conn.close()
    return rows


@router.get("/patients/{patient_id}/sdoh")
def get_patient_sdoh(patient_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM sdoh_assessment WHERE patient_id = ?", (patient_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


# ── Actions ───────────────────────────────────────────────────────────────────

@router.patch("/gaps/{gap_id}/close")
def close_gap(gap_id: int, body: CloseGapBody):
    conn = get_connection()
    row = conn.execute("SELECT patient_id FROM care_gaps WHERE gap_id=?", (gap_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Gap not found")
    conn.execute(
        "UPDATE care_gaps SET gap_status='CLOSED', closed_at=datetime('now'), "
        "closed_by=?, closure_note=? WHERE gap_id=?",
        (body.closed_by, body.closure_note, gap_id),
    )
    conn.commit()
    update_risk_profile(row["patient_id"], conn)
    conn.commit()
    conn.close()
    return {"ok": True}


@router.patch("/tasks/{task_id}/complete")
def complete_task(task_id: int, body: CompleteTaskBody):
    conn = get_connection()
    exists = conn.execute("SELECT 1 FROM care_tasks WHERE task_id=?", (task_id,)).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Task not found")
    conn.execute(
        "UPDATE care_tasks SET status='COMPLETED', completed_at=datetime('now'), "
        "completion_note=? WHERE task_id=?",
        (body.completion_note, task_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}
