"""
Seed script for FulcrumCare MVP.
Run directly:  python db/seed.py
Or call:       from db.seed import seed_database; seed_database()
"""

import os
import sys
import random
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from faker import Faker
from db.schema import get_connection, init_db, drop_all_tables, SCHEMA_SQL

fake = Faker()
Faker.seed(42)
random.seed(42)

TODAY = date(2026, 4, 12)


# ── Date helpers ──────────────────────────────────────────────────────────────

def rdate(days_ago_max, days_ago_min=0):
    lo = TODAY - timedelta(days=days_ago_max)
    hi = TODAY - timedelta(days=days_ago_min)
    delta = (hi - lo).days
    return (lo + timedelta(days=random.randint(0, max(delta, 0)))).isoformat()

def dob_for_age(age):
    base = TODAY.replace(year=TODAY.year - age)
    return (base - timedelta(days=random.randint(0, 364))).isoformat()


# ── CDT / ICD reference data ──────────────────────────────────────────────────

CDT = {
    "D0120": "Periodic oral evaluation – established patient",
    "D0150": "Comprehensive oral examination – new/established patient",
    "D0180": "Comprehensive periodontal evaluation",
    "D1110": "Prophylaxis – adult",
    "D1120": "Prophylaxis – child",
    "D1206": "Topical fluoride varnish",
    "D1351": "Sealant – per tooth",
    "D4341": "Periodontal scaling and root planing – 4+ teeth/quadrant",
}

PREVENTIVE_CODES  = {"D0120", "D0150", "D1110", "D1120"}
ORAL_EVAL_CODES   = {"D0120", "D0150"}
PERIO_EVAL_CODES  = {"D0180"}
FLUORIDE_CODES    = {"D1206"}
SEALANT_CODES     = {"D1351"}


# ── Measures ──────────────────────────────────────────────────────────────────

MEASURES = [
    ("PREV_DENTAL_12M",         "Preventive Dental Visit",
     "Enrolled patients who received a preventive dental service in the past 12 months.",
     "Preventive", 1.5, "all"),
    ("ORAL_EVAL_DIABETES",      "Oral Evaluation – Adults with Diabetes",
     "Adults 18+ with diabetes who received an oral evaluation in the reporting year.",
     "Chronic Disease", 2.0, "diabetic"),
    ("PERIODONTAL_EVAL",        "Periodontal Evaluation",
     "Adults 18+ who received a comprehensive periodontal evaluation.",
     "Preventive", 1.5, "adult"),
    ("TOPICAL_FLUORIDE_HIGHRISK","Topical Fluoride Application",
     "High-risk patients who received topical fluoride application.",
     "Preventive", 1.0, "high_risk"),
    ("SEALANTS_CHILDREN",       "Dental Sealants for Children",
     "Children aged 6–14 who received at least one dental sealant.",
     "Preventive – Pediatric", 1.2, "child"),
]


# ── Featured patients (narrative anchor for demos) ────────────────────────────

FEATURED = [
    # (first, last, age, gender, adi, diabetic, htn, perio, transport, comm, cost, fear, schedule)
    ("Isaiah",   "Pebbles",   65, "M", 10, 1, 1, 1, 1, 0, 1, 1, 0),  # Very High
    ("Patricia", "Johnson",   52, "F",  6, 1, 0, 0, 0, 0, 1, 0, 0),  # Medium
    ("Michael",  "Ross",      34, "M",  7, 0, 0, 0, 0, 0, 0, 0, 1),  # Medium (has appt)
    ("Emily",    "Burk",      51, "F",  8, 0, 0, 1, 1, 0, 0, 1, 0),  # High
    ("Robert",   "Williams",  55, "M",  7, 1, 1, 0, 0, 0, 1, 0, 0),  # High
    ("Jade",     "Johnson",   35, "F",  8, 0, 0, 0, 1, 0, 1, 0, 0),  # High
    ("Marcus",   "Johnson",    9, "M",  6, 0, 0, 0, 0, 0, 0, 1, 0),  # Medium (child)
    ("Dorothy",  "Baker",     72, "F",  9, 1, 1, 0, 1, 0, 1, 0, 0),  # Very High
    ("Keisha",   "Williams",  41, "F",  8, 0, 0, 0, 1, 1, 1, 0, 0),  # High
    ("Carlos",   "Mendez",    47, "M",  9, 1, 0, 1, 0, 1, 1, 0, 0),  # High
]


# ── Main seed function ────────────────────────────────────────────────────────

def seed_database():
    drop_all_tables()
    conn = get_connection()
    conn.executescript(SCHEMA_SQL)
    conn.commit()

    # ── Clinics ──────────────────────────────────────────────────────────────
    conn.execute("INSERT INTO clinics (name, address, city) VALUES (?,?,?)",
                 ("Hillhouse Community Health Center", "300 George St", "New Haven"))
    conn.execute("INSERT INTO clinics (name, address, city) VALUES (?,?,?)",
                 ("Westside Community Dental", "1 Whalley Ave", "West Haven"))
    conn.commit()

    # ── Providers ────────────────────────────────────────────────────────────
    providers = [
        ("Dr. James Smith",  "dentist", "General Dentistry", 1),
        ("Dr. Maria Garcia", "dentist", "General Dentistry", 1),
        ("Dr. David Chen",   "dentist", "Periodontics",      2),
    ]
    for p in providers:
        conn.execute("INSERT INTO providers (name, role, specialty, clinic_id) VALUES (?,?,?,?)", p)
    conn.commit()

    # ── Care coordinators ─────────────────────────────────────────────────────
    conn.execute("INSERT INTO care_coordinators (name, email) VALUES (?,?)",
                 ("Lisa Martinez", "lmartinez@hillhouse.org"))
    conn.execute("INSERT INTO care_coordinators (name, email) VALUES (?,?)",
                 ("Amanda Foster", "afoster@hillhouse.org"))
    conn.commit()

    # ── Measures ─────────────────────────────────────────────────────────────
    for m in MEASURES:
        conn.execute(
            "INSERT INTO measure_reference (measure_id,name,description,category,priority_weight,applies_to)"
            " VALUES (?,?,?,?,?,?)", m)
    conn.commit()

    # ── Insert patients ───────────────────────────────────────────────────────
    provider_ids = [1, 2, 3]
    coord_ids    = [1, 2]
    patient_ids  = []

    # Featured patients
    for i, (fn, ln, age, gender, adi, diab, htn, perio, trans, comm, cost, fear, sched) in enumerate(FEATURED):
        pid = _insert_patient(
            conn, fn, ln, age, gender, adi,
            diab, htn, perio,
            provider_ids[i % 3], coord_ids[i % 2],
        )
        _insert_sdoh(conn, pid, trans, comm, cost, fear, i % 2 == 0)
        patient_ids.append(pid)

    # Random patients
    names_pool = _random_name_pool(65)
    for j, (fn, ln, age, gender) in enumerate(names_pool):
        adi   = _skewed_adi()
        diab  = 1 if (age >= 30 and random.random() < 0.28) else 0
        htn   = 1 if (age >= 35 and random.random() < 0.35) else 0
        perio = 1 if (age >= 25 and random.random() < 0.22) else 0
        pid = _insert_patient(
            conn, fn, ln, age, gender, adi,
            diab, htn, perio,
            random.choice(provider_ids), random.choice(coord_ids),
        )
        _insert_sdoh_random(conn, pid, adi)
        patient_ids.append(pid)

    conn.commit()

    # ── Clinical data ─────────────────────────────────────────────────────────
    for pid in patient_ids:
        _insert_diagnoses(conn, pid)
        _insert_encounters_and_procedures(conn, pid)
    conn.commit()

    # ── Care gaps ─────────────────────────────────────────────────────────────
    for pid in patient_ids:
        _compute_and_insert_gaps(conn, pid)
    conn.commit()

    # ── Pre-seeded outreach / engagement ──────────────────────────────────────
    _seed_outreach(conn, patient_ids)
    conn.commit()

    # ── Pre-seeded care tasks ─────────────────────────────────────────────────
    _seed_tasks(conn, patient_ids)
    conn.commit()

    # ── Risk profiles ─────────────────────────────────────────────────────────
    from utils.calculations import update_risk_profile
    for pid in patient_ids:
        update_risk_profile(pid, conn)
    conn.commit()
    conn.close()


# ── Patient helpers ───────────────────────────────────────────────────────────

def _insert_patient(conn, fn, ln, age, gender, adi, diab, htn, perio, prov_id, coord_id):
    mid = f"MCO{random.randint(100000, 999999)}"
    phone = f"203-{random.randint(200,999)}-{random.randint(1000,9999)}"
    city  = random.choice(["New Haven", "West Haven", "Hamden", "East Haven", "Ansonia"])
    zipc  = random.choice(["06511", "06516", "06517", "06501", "06518"])
    addr  = fake.street_address()
    cur = conn.execute(
        """INSERT INTO patients
           (first_name, last_name, dob, age, gender, medicaid_id, phone,
            address, city, zip, adi_decile,
            assigned_provider_id, assigned_coordinator_id,
            is_diabetic, has_hypertension, has_periodontitis, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (fn, ln, dob_for_age(age), age, gender, mid, phone,
         addr, city, zipc, adi,
         prov_id, coord_id,
         diab, htn, perio,
         rdate(730, 365)),
    )
    return cur.lastrowid


def _skewed_adi():
    # Medicaid pop skews toward higher deprivation (deciles 6-10)
    return random.choices(range(1, 11),
                          weights=[1, 2, 3, 4, 6, 8, 10, 12, 10, 8])[0]


def _insert_sdoh(conn, pid, transport, comm, cost, fear, work):
    conn.execute(
        """INSERT INTO sdoh_assessment
           (patient_id, transportation, communication_challenges, cost_anxiety,
            dental_fear, work_schedule_constraints, assessed_at)
           VALUES (?,?,?,?,?,?,?)""",
        (pid, transport, comm, cost, fear, int(work), rdate(180, 7)),
    )


def _insert_sdoh_random(conn, pid, adi):
    # Higher ADI → higher probability of barriers
    p = min(0.85, 0.2 + (adi - 1) * 0.07)
    conn.execute(
        """INSERT INTO sdoh_assessment
           (patient_id, transportation, communication_challenges, cost_anxiety,
            dental_fear, work_schedule_constraints, assessed_at)
           VALUES (?,?,?,?,?,?,?)""",
        (pid,
         int(random.random() < p * 0.7),
         int(random.random() < p * 0.4),
         int(random.random() < p * 0.9),
         int(random.random() < 0.3),
         int(random.random() < 0.4),
         rdate(180, 7)),
    )


def _insert_diagnoses(conn, pid):
    row = conn.execute(
        "SELECT age, is_diabetic, has_hypertension, has_periodontitis FROM patients WHERE patient_id=?",
        (pid,)
    ).fetchone()
    if row["is_diabetic"]:
        conn.execute(
            "INSERT INTO diagnoses (patient_id, icd_code, description, diagnosis_date, is_active)"
            " VALUES (?,?,?,?,1)",
            (pid, "E11.9", "Type 2 diabetes mellitus without complications", rdate(1095, 365)),
        )
    if row["has_hypertension"]:
        conn.execute(
            "INSERT INTO diagnoses (patient_id, icd_code, description, diagnosis_date, is_active)"
            " VALUES (?,?,?,?,1)",
            (pid, "I10", "Essential hypertension", rdate(1095, 180)),
        )
    if row["has_periodontitis"]:
        conn.execute(
            "INSERT INTO diagnoses (patient_id, icd_code, description, diagnosis_date, is_active)"
            " VALUES (?,?,?,?,1)",
            (pid, "K05.30", "Chronic periodontitis, unspecified", rdate(730, 90)),
        )


def _insert_encounters_and_procedures(conn, pid):
    row = conn.execute(
        "SELECT age, assigned_provider_id FROM patients WHERE patient_id=?", (pid,)
    ).fetchone()
    age, prov = row["age"], row["assigned_provider_id"]

    # ~55% of patients had a dental visit in the past 24 months
    if random.random() < 0.55:
        enc_date = rdate(730, 0)
        cur = conn.execute(
            "INSERT INTO encounters (patient_id, provider_id, encounter_type, encounter_date)"
            " VALUES (?,?,?,?)",
            (pid, prov, "dental", enc_date),
        )
        eid = cur.lastrowid
        code = random.choice(["D0120", "D0150", "D1110" if age >= 18 else "D1120"])
        conn.execute(
            "INSERT INTO procedures (patient_id, encounter_id, proc_code, proc_description, proc_date)"
            " VALUES (?,?,?,?,?)",
            (pid, eid, code, CDT[code], enc_date),
        )
        # Some also got perio eval, fluoride, or sealant
        if random.random() < 0.35:
            extra = "D0180" if age >= 18 else "D1351" if 6 <= age <= 14 else "D1206"
            conn.execute(
                "INSERT INTO procedures (patient_id, encounter_id, proc_code, proc_description, proc_date)"
                " VALUES (?,?,?,?,?)",
                (pid, eid, extra, CDT[extra], enc_date),
            )

    # ~12% had an ED visit in the past year
    if random.random() < 0.12:
        ed_date = rdate(365, 7)
        conn.execute(
            "INSERT INTO encounters (patient_id, provider_id, encounter_type, encounter_date, notes)"
            " VALUES (?,?,?,?,?)",
            (pid, None, "ED", ed_date, "ED visit – dental pain / abscess"),
        )


# ── Care-gap logic ────────────────────────────────────────────────────────────

def _compute_and_insert_gaps(conn, pid):
    row = conn.execute(
        "SELECT age, is_diabetic, has_periodontitis, adi_decile FROM patients WHERE patient_id=?",
        (pid,)
    ).fetchone()
    age, diab, perio, adi = row["age"], row["is_diabetic"], row["has_periodontitis"], row["adi_decile"]
    cutoff_12m = (TODAY - timedelta(days=365)).isoformat()

    procs = set(conn.execute(
        "SELECT proc_code FROM procedures WHERE patient_id=? AND proc_date>=?",
        (pid, cutoff_12m)
    ).fetchall())
    proc_codes = {r[0] for r in procs}

    def has(codes):
        return bool(proc_codes & codes)

    def gap(measure_id, status):
        conn.execute(
            "INSERT INTO care_gaps (patient_id, measure_id, gap_status, last_evaluated_at)"
            " VALUES (?,?,?,?)",
            (pid, measure_id, status, TODAY.isoformat()),
        )

    # PREV_DENTAL_12M – all patients
    gap("PREV_DENTAL_12M", "CLOSED" if has(PREVENTIVE_CODES) else "OPEN")

    # ORAL_EVAL_DIABETES – diabetics only
    if diab:
        gap("ORAL_EVAL_DIABETES", "CLOSED" if has(ORAL_EVAL_CODES) else "OPEN")

    # PERIODONTAL_EVAL – adults 18+
    if age >= 18:
        gap("PERIODONTAL_EVAL", "CLOSED" if has(PERIO_EVAL_CODES) else "OPEN")

    # TOPICAL_FLUORIDE – high risk (ADI >= 7 or periodontitis)
    if adi >= 7 or perio:
        gap("TOPICAL_FLUORIDE_HIGHRISK", "CLOSED" if has(FLUORIDE_CODES) else "OPEN")

    # SEALANTS_CHILDREN – ages 6-14
    if 6 <= age <= 14:
        gap("SEALANTS_CHILDREN", "CLOSED" if has(SEALANT_CODES) else "OPEN")


# ── Pre-seed outreach history ─────────────────────────────────────────────────

def _seed_outreach(conn, patient_ids):
    METHODS   = ["call", "call", "call", "text", "email"]
    OUTCOMES  = ["voicemail", "no_answer", "reached", "voicemail", "no_answer"]

    # Give ~40 patients pre-existing outreach
    for pid in random.sample(patient_ids, min(40, len(patient_ids))):
        coord = conn.execute(
            "SELECT assigned_coordinator_id FROM patients WHERE patient_id=?", (pid,)
        ).fetchone()[0]
        n_attempts = random.randint(1, 4)
        for _ in range(n_attempts):
            method  = random.choice(METHODS)
            outcome = random.choice(OUTCOMES)
            conn.execute(
                "INSERT INTO outreach_attempts (patient_id, coordinator_id, method, outcome, attempt_time)"
                " VALUES (?,?,?,?,?)",
                (pid, coord, method, outcome, rdate(60, 1)),
            )
            # Add engagement event for positive outcomes
            if outcome == "reached":
                conn.execute(
                    "INSERT INTO engagement_events (patient_id, coordinator_id, event_type, outcome, event_timestamp)"
                    " VALUES (?,?,?,?,?)",
                    (pid, coord, "call_answered", "positive", rdate(60, 1)),
                )

    # Give ~10 patients a scheduled appointment (very recent)
    for pid in random.sample(patient_ids, min(10, len(patient_ids))):
        coord = conn.execute(
            "SELECT assigned_coordinator_id FROM patients WHERE patient_id=?", (pid,)
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO engagement_events (patient_id, coordinator_id, event_type, outcome, event_timestamp)"
            " VALUES (?,?,?,?,?)",
            (pid, coord, "appt_scheduled", "positive", rdate(14, 1)),
        )

    # Force featured patient #2 (Michael Ross, index 2) to have a scheduled appt
    mr_pid = patient_ids[2]
    coord_mr = conn.execute(
        "SELECT assigned_coordinator_id FROM patients WHERE patient_id=?", (mr_pid,)
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO engagement_events (patient_id, coordinator_id, event_type, outcome, event_timestamp)"
        " VALUES (?,?,?,?,?)",
        (mr_pid, coord_mr, "appt_scheduled", "positive", rdate(5, 1)),
    )


# ── Pre-seed care tasks ───────────────────────────────────────────────────────

def _seed_tasks(conn, patient_ids):
    isaiah_pid  = patient_ids[0]   # Isaiah Pebbles
    emily_pid   = patient_ids[3]   # Emily Burk
    robert_pid  = patient_ids[4]   # Robert Williams
    dorothy_pid = patient_ids[7]   # Dorothy Baker

    tasks = [
        # (pid, coord_id, prov_id, intent, message, status, days_ago)
        (isaiah_pid, 1, 1,
         "Schedule dental exam / evaluation",
         "Patient has 3 open care gaps including overdue diabetes oral eval. Please schedule comprehensive exam.",
         "OPEN", 3),
        (emily_pid, 2, 2,
         "Address overdue periodontal maintenance",
         "Ms. Burk is overdue for periodontal eval. Previous coordinator noted transportation barriers – may need assistance.",
         "OPEN", 7),
        (dorothy_pid, 1, 1,
         "Follow up after ED visit for NTDC",
         "Patient visited ED for dental pain on 2026-03-28. Needs urgent dental appointment and care coordination.",
         "OPEN", 14),
        (robert_pid, 1, 2,
         "Schedule dental exam / evaluation",
         "Annual diabetes dental eval overdue. Patient has been responsive to outreach.",
         "COMPLETED", 21),
    ]
    for pid, cid, pvid, intent, msg, status, days in tasks:
        created = (TODAY - timedelta(days=days)).isoformat()
        completed = (TODAY - timedelta(days=days - 5)).isoformat() if status == "COMPLETED" else None
        note = "Appointment scheduled for next available slot." if status == "COMPLETED" else None
        conn.execute(
            """INSERT INTO care_tasks
               (patient_id, assigned_coordinator_id, created_by_provider_id,
                message_intent, message, status, created_at, completed_at, completion_note)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (pid, cid, pvid, intent, msg, status, created, completed, note),
        )


# ── Name pool for random patients ─────────────────────────────────────────────

def _random_name_pool(n):
    """Return list of (first, last, age, gender) tuples."""
    pool = []
    # age distribution: 15 children, 40 working-age adults, 10 elderly
    age_dist = (
        [random.randint(6, 14)  for _ in range(15)] +
        [random.randint(18, 64) for _ in range(40)] +
        [random.randint(65, 85) for _ in range(10)]
    )
    random.shuffle(age_dist)
    for i in range(n):
        gender = random.choice(["M", "F"])
        first  = fake.first_name_male() if gender == "M" else fake.first_name_female()
        last   = fake.last_name()
        age    = age_dist[i]
        pool.append((first, last, age, gender))
    return pool


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Seeding FulcrumCare demo database…")
    seed_database()
    conn = get_connection()
    patients = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    gaps     = conn.execute("SELECT COUNT(*) FROM care_gaps WHERE gap_status='OPEN'").fetchone()[0]
    tasks    = conn.execute("SELECT COUNT(*) FROM care_tasks").fetchone()[0]
    conn.close()
    print(f"Done. {patients} patients | {gaps} open care gaps | {tasks} care tasks")
