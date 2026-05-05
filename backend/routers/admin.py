from fastapi import APIRouter, Query
from typing import Optional
import pandas as pd

from db.schema import get_connection

router = APIRouter(tags=["admin"])


def _clinic_join(clinic_id: Optional[int]):
    if clinic_id:
        return (
            "JOIN providers pv ON p.assigned_provider_id = pv.provider_id",
            f"AND pv.clinic_id = {clinic_id}",
        )
    return "", ""


@router.get("/clinics")
def list_clinics():
    conn = get_connection()
    rows = pd.read_sql_query("SELECT clinic_id, name FROM clinics", conn).to_dict(orient="records")
    conn.close()
    return rows


@router.get("/stats")
def admin_stats(clinic_id: Optional[int] = Query(None)):
    jn, wh = _clinic_join(clinic_id)
    conn = get_connection()

    total = conn.execute(f"SELECT COUNT(*) FROM patients p {jn} WHERE p.is_active=1 {wh}").fetchone()[0]
    open_gaps = conn.execute(
        f"SELECT COUNT(*) FROM care_gaps cg JOIN patients p ON cg.patient_id=p.patient_id {jn} WHERE cg.gap_status='OPEN' {wh}"
    ).fetchone()[0]
    closed_gaps = conn.execute(
        f"SELECT COUNT(*) FROM care_gaps cg JOIN patients p ON cg.patient_id=p.patient_id {jn} WHERE cg.gap_status='CLOSED' {wh}"
    ).fetchone()[0]
    high_risk = conn.execute(
        f"SELECT COUNT(*) FROM patient_risk_profile pr JOIN patients p ON pr.patient_id=p.patient_id {jn} WHERE pr.risk_bucket IN ('HIGH','VERY_HIGH') {wh}"
    ).fetchone()[0]
    diabetic_pct = conn.execute(
        f"SELECT ROUND(100.0*SUM(p.is_diabetic)/COUNT(*),1) FROM patients p {jn} WHERE p.is_active=1 {wh}"
    ).fetchone()[0] or 0
    open_tasks = conn.execute("SELECT COUNT(*) FROM care_tasks WHERE status='OPEN'").fetchone()[0]
    total_gaps = open_gaps + closed_gaps
    conn.close()

    return {
        "total": total,
        "open_gaps": open_gaps,
        "closed_gaps": closed_gaps,
        "closure_rate": round(closed_gaps / max(total_gaps, 1) * 100, 1),
        "high_risk": high_risk,
        "diabetic_pct": diabetic_pct,
        "open_tasks": open_tasks,
    }


@router.get("/gaps-by-measure")
def gaps_by_measure(clinic_id: Optional[int] = Query(None)):
    jn, wh = _clinic_join(clinic_id)
    conn = get_connection()
    rows = pd.read_sql_query(
        f"""SELECT mr.name as measure, cg.gap_status, COUNT(*) as count
            FROM care_gaps cg
            JOIN measure_reference mr ON cg.measure_id=mr.measure_id
            JOIN patients p ON cg.patient_id=p.patient_id
            {jn}
            WHERE 1=1 {wh}
            GROUP BY mr.name, cg.gap_status""",
        conn,
    )
    conn.close()
    # Pivot to [{measure, OPEN, CLOSED}]
    if rows.empty:
        return []
    pivot = rows.pivot_table(index="measure", columns="gap_status", values="count", fill_value=0).reset_index()
    return pivot.to_dict(orient="records")


@router.get("/risk-distribution")
def risk_distribution(clinic_id: Optional[int] = Query(None)):
    jn, wh = _clinic_join(clinic_id)
    conn = get_connection()
    rows = pd.read_sql_query(
        f"""SELECT pr.risk_bucket, COUNT(*) as count
            FROM patient_risk_profile pr
            JOIN patients p ON pr.patient_id=p.patient_id
            {jn}
            WHERE 1=1 {wh}
            GROUP BY pr.risk_bucket""",
        conn,
    ).to_dict(orient="records")
    conn.close()
    return rows


@router.get("/adi-distribution")
def adi_distribution(clinic_id: Optional[int] = Query(None)):
    jn, wh = _clinic_join(clinic_id)
    conn = get_connection()
    rows = pd.read_sql_query(
        f"""SELECT p.adi_decile,
               COUNT(*) as total,
               SUM(CASE WHEN pr.risk_bucket IN ('HIGH','VERY_HIGH') THEN 1 ELSE 0 END) as high_risk
            FROM patients p
            {jn}
            LEFT JOIN patient_risk_profile pr ON p.patient_id=pr.patient_id
            WHERE p.is_active=1 {wh}
            GROUP BY p.adi_decile ORDER BY p.adi_decile""",
        conn,
    ).to_dict(orient="records")
    conn.close()
    return rows


@router.get("/compliance")
def measure_compliance(clinic_id: Optional[int] = Query(None)):
    jn, wh = _clinic_join(clinic_id)
    conn = get_connection()
    rows = pd.read_sql_query(
        f"""SELECT mr.name as measure,
               COUNT(*) as total,
               SUM(CASE WHEN cg.gap_status='CLOSED' THEN 1 ELSE 0 END) as closed,
               ROUND(100.0*SUM(CASE WHEN cg.gap_status='CLOSED' THEN 1 ELSE 0 END)/COUNT(*),1) as pct
            FROM care_gaps cg
            JOIN measure_reference mr ON cg.measure_id=mr.measure_id
            JOIN patients p ON cg.patient_id=p.patient_id
            {jn}
            WHERE cg.gap_status != 'NOT_APPLICABLE' {wh}
            GROUP BY mr.name ORDER BY pct DESC""",
        conn,
    ).to_dict(orient="records")
    conn.close()
    return rows


@router.get("/providers")
def provider_performance():
    conn = get_connection()
    rows = pd.read_sql_query(
        """SELECT prov.name as provider, cl.name as clinic,
               COUNT(DISTINCT p.patient_id) as patients,
               COUNT(DISTINCT CASE WHEN cg.gap_status='OPEN'   THEN cg.gap_id END) as open_gaps,
               COUNT(DISTINCT CASE WHEN cg.gap_status='CLOSED' THEN cg.gap_id END) as closed_gaps,
               ROUND(100.0*
                   COUNT(DISTINCT CASE WHEN cg.gap_status='CLOSED' THEN cg.gap_id END)/
                   NULLIF(COUNT(DISTINCT cg.gap_id),0),1) as closure_pct,
               ROUND(AVG(pr.composite_risk),1) as avg_risk
            FROM providers prov
            JOIN clinics cl ON prov.clinic_id=cl.clinic_id
            JOIN patients p ON p.assigned_provider_id=prov.provider_id
            LEFT JOIN care_gaps cg ON cg.patient_id=p.patient_id
            LEFT JOIN patient_risk_profile pr ON pr.patient_id=p.patient_id
            WHERE p.is_active=1
            GROUP BY prov.provider_id ORDER BY patients DESC""",
        conn,
    ).to_dict(orient="records")
    conn.close()
    return rows


@router.get("/outreach-summary")
def outreach_summary():
    conn = get_connection()
    rows = pd.read_sql_query(
        """SELECT method,
               COUNT(*) as attempts,
               SUM(CASE WHEN outcome='reached' THEN 1 ELSE 0 END) as reached,
               ROUND(100.0*SUM(CASE WHEN outcome='reached' THEN 1 ELSE 0 END)/COUNT(*),1) as reach_rate
           FROM outreach_attempts
           WHERE attempt_time >= date('now','-30 days')
           GROUP BY method ORDER BY attempts DESC""",
        conn,
    ).to_dict(orient="records")
    conn.close()
    return rows


@router.get("/data-quality")
def data_quality():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM patients WHERE is_active=1").fetchone()[0]
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
    never_contacted = conn.execute(
        "SELECT COUNT(*) FROM patients p WHERE NOT EXISTS "
        "(SELECT 1 FROM outreach_attempts oa WHERE oa.patient_id=p.patient_id) AND p.is_active=1"
    ).fetchone()[0]
    reached = conn.execute(
        "SELECT COUNT(DISTINCT patient_id) FROM outreach_attempts WHERE outcome='reached'"
    ).fetchone()[0]
    appt_scheduled = conn.execute(
        "SELECT COUNT(DISTINCT patient_id) FROM engagement_events WHERE event_type='appt_scheduled'"
    ).fetchone()[0]
    conn.close()

    return {
        "sdoh_coverage": round((1 - no_sdoh / max(total, 1)) * 100, 1),
        "risk_coverage":  round((1 - no_risk / max(total, 1)) * 100, 1),
        "gap_coverage":   round((1 - no_gaps / max(total, 1)) * 100, 1),
        "engagement": {
            "never_contacted": never_contacted,
            "reached": reached,
            "appt_scheduled": appt_scheduled,
        },
    }
