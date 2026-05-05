"""
Risk stratification engine for the FulcrumCare MVP.

Composite risk = 0.50 * EngagementRisk + 0.30 * ClinicalScore + 0.20 * SDOHScore

EngagementRisk is *inverted*: patients with no coordinator contact score HIGH (hard to reach).
  - No outreach history           → 78
  - Attempted, never reached      → 62
  - Reached at least once         → 35
  - Appointment scheduled/kept    → 14

ClinicalScore: open care gaps (weighted) + chronic conditions + ED utilisation.

SDOHScore: ADI decile + coordinator-reported SDOH barriers.

Thresholds: VERY_HIGH ≥ 72 | HIGH ≥ 52 | MEDIUM ≥ 32 | LOW < 32
"""

import os
import sys
from datetime import date, timedelta

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from db.schema import get_connection

TODAY = date.today()
WINDOW_90 = (TODAY - timedelta(days=90)).isoformat()
WINDOW_365 = (TODAY - timedelta(days=365)).isoformat()


# ── Sub-scores ────────────────────────────────────────────────────────────────

def _engagement_risk(patient_id: int, conn) -> float:
    attempts = pd.read_sql_query(
        "SELECT outcome FROM outreach_attempts WHERE patient_id=? AND attempt_time>=?",
        conn, params=(patient_id, WINDOW_90),
    )
    events = pd.read_sql_query(
        "SELECT event_type FROM engagement_events WHERE patient_id=? AND event_timestamp>=?",
        conn, params=(patient_id, WINDOW_90),
    )
    if attempts.empty and events.empty:
        return 78.0

    outcomes = set(attempts["outcome"].tolist()) if not attempts.empty else set()
    etypes   = set(events["event_type"].tolist()) if not events.empty else set()

    if etypes & {"appt_scheduled", "appt_completed"}:
        return 14.0
    if "reached" in outcomes or "call_answered" in etypes:
        return 35.0
    if not attempts.empty:
        return 62.0
    return 78.0


def _clinical_score(patient_id: int, conn) -> float:
    gaps = pd.read_sql_query(
        """SELECT mr.priority_weight
           FROM care_gaps cg
           JOIN measure_reference mr ON cg.measure_id = mr.measure_id
           WHERE cg.patient_id=? AND cg.gap_status='OPEN'""",
        conn, params=(patient_id,),
    )
    gap_score = float(gaps["priority_weight"].sum()) * 14.0 if not gaps.empty else 0.0

    row = conn.execute(
        "SELECT is_diabetic, has_hypertension, has_periodontitis FROM patients WHERE patient_id=?",
        (patient_id,),
    ).fetchone()
    chronic = (row["is_diabetic"] + row["has_hypertension"] + row["has_periodontitis"]) * 9.0

    ed = conn.execute(
        "SELECT COUNT(*) FROM encounters WHERE patient_id=? AND encounter_type='ED' AND encounter_date>=?",
        (patient_id, WINDOW_365),
    ).fetchone()[0]
    ed_score = ed * 14.0

    return min(100.0, gap_score + chronic + ed_score)


def _sdoh_score(patient_id: int, conn) -> float:
    p = conn.execute(
        "SELECT adi_decile FROM patients WHERE patient_id=?", (patient_id,)
    ).fetchone()
    adi_component = ((p["adi_decile"] - 1) / 9.0) * 58.0

    s = conn.execute(
        "SELECT transportation, communication_challenges, cost_anxiety, dental_fear, work_schedule_constraints "
        "FROM sdoh_assessment WHERE patient_id=?",
        (patient_id,),
    ).fetchone()
    if s:
        flag_score = (
            s["transportation"]            * 14
            + s["communication_challenges"]  *  8
            + s["cost_anxiety"]              * 13
            + s["dental_fear"]               *  8
            + s["work_schedule_constraints"] *  7
        )
    else:
        flag_score = 0.0

    return min(100.0, adi_component + min(42.0, flag_score))


# ── Composite ─────────────────────────────────────────────────────────────────

def _bucket(score: float) -> str:
    if score >= 72:
        return "VERY_HIGH"
    if score >= 52:
        return "HIGH"
    if score >= 32:
        return "MEDIUM"
    return "LOW"


def compute_risk(patient_id: int, conn) -> dict:
    es = _engagement_risk(patient_id, conn)
    cs = _clinical_score(patient_id, conn)
    ss = _sdoh_score(patient_id, conn)
    composite = round(0.50 * es + 0.30 * cs + 0.20 * ss, 1)
    return {
        "engagement_score": round(es, 1),
        "clinical_score":   round(cs, 1),
        "sdoh_score":       round(ss, 1),
        "composite_risk":   composite,
        "risk_bucket":      _bucket(composite),
    }


def update_risk_profile(patient_id: int, conn):
    r = compute_risk(patient_id, conn)
    conn.execute(
        """INSERT INTO patient_risk_profile
               (patient_id, engagement_score, clinical_score, sdoh_score, composite_risk, risk_bucket, computed_at)
           VALUES (?,?,?,?,?,?,datetime('now'))
           ON CONFLICT(patient_id) DO UPDATE SET
               engagement_score=excluded.engagement_score,
               clinical_score=excluded.clinical_score,
               sdoh_score=excluded.sdoh_score,
               composite_risk=excluded.composite_risk,
               risk_bucket=excluded.risk_bucket,
               computed_at=excluded.computed_at""",
        (patient_id, r["engagement_score"], r["clinical_score"],
         r["sdoh_score"], r["composite_risk"], r["risk_bucket"]),
    )
    conn.commit()


def recompute_all(conn):
    ids = [r[0] for r in conn.execute("SELECT patient_id FROM patients WHERE is_active=1").fetchall()]
    for pid in ids:
        update_risk_profile(pid, conn)
