import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fulcrumcare.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS clinics (
    clinic_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    address     TEXT,
    city        TEXT,
    state       TEXT DEFAULT 'CT'
);

CREATE TABLE IF NOT EXISTS providers (
    provider_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    role        TEXT NOT NULL,
    specialty   TEXT,
    clinic_id   INTEGER REFERENCES clinics(clinic_id)
);

CREATE TABLE IF NOT EXISTS care_coordinators (
    coordinator_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    email          TEXT
);

CREATE TABLE IF NOT EXISTS patients (
    patient_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name             TEXT NOT NULL,
    last_name              TEXT NOT NULL,
    dob                    TEXT NOT NULL,
    age                    INTEGER NOT NULL,
    gender                 TEXT,
    medicaid_id            TEXT UNIQUE,
    phone                  TEXT,
    address                TEXT,
    city                   TEXT,
    state                  TEXT DEFAULT 'CT',
    zip                    TEXT,
    adi_decile             INTEGER DEFAULT 5,
    assigned_provider_id   INTEGER REFERENCES providers(provider_id),
    assigned_coordinator_id INTEGER REFERENCES care_coordinators(coordinator_id),
    is_diabetic            INTEGER DEFAULT 0,
    has_hypertension       INTEGER DEFAULT 0,
    has_periodontitis      INTEGER DEFAULT 0,
    is_active              INTEGER DEFAULT 1,
    created_at             TEXT
);

CREATE TABLE IF NOT EXISTS measure_reference (
    measure_id      TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT,
    category        TEXT,
    priority_weight REAL DEFAULT 1.0,
    applies_to      TEXT DEFAULT 'all'
);

CREATE TABLE IF NOT EXISTS encounters (
    encounter_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id     INTEGER NOT NULL REFERENCES patients(patient_id),
    provider_id    INTEGER REFERENCES providers(provider_id),
    encounter_type TEXT,
    encounter_date TEXT NOT NULL,
    notes          TEXT
);

CREATE TABLE IF NOT EXISTS procedures (
    procedure_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL REFERENCES patients(patient_id),
    encounter_id    INTEGER REFERENCES encounters(encounter_id),
    proc_code       TEXT NOT NULL,
    proc_description TEXT,
    proc_date       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS diagnoses (
    diagnosis_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id     INTEGER NOT NULL REFERENCES patients(patient_id),
    icd_code       TEXT NOT NULL,
    description    TEXT,
    diagnosis_date TEXT,
    is_active      INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS sdoh_assessment (
    assessment_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id               INTEGER UNIQUE NOT NULL REFERENCES patients(patient_id),
    transportation           INTEGER DEFAULT 0,
    communication_challenges INTEGER DEFAULT 0,
    cost_anxiety             INTEGER DEFAULT 0,
    dental_fear              INTEGER DEFAULT 0,
    work_schedule_constraints INTEGER DEFAULT 0,
    assessed_at              TEXT
);

CREATE TABLE IF NOT EXISTS care_gaps (
    gap_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id       INTEGER NOT NULL REFERENCES patients(patient_id),
    measure_id       TEXT NOT NULL REFERENCES measure_reference(measure_id),
    gap_status       TEXT DEFAULT 'OPEN',
    due_date         TEXT,
    last_evaluated_at TEXT,
    closed_at        TEXT,
    closed_by        TEXT,
    closure_note     TEXT
);

CREATE TABLE IF NOT EXISTS patient_risk_profile (
    profile_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id       INTEGER UNIQUE NOT NULL REFERENCES patients(patient_id),
    engagement_score REAL DEFAULT 50.0,
    clinical_score   REAL DEFAULT 0.0,
    sdoh_score       REAL DEFAULT 0.0,
    composite_risk   REAL DEFAULT 0.0,
    risk_bucket      TEXT DEFAULT 'LOW',
    computed_at      TEXT
);

CREATE TABLE IF NOT EXISTS care_tasks (
    task_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id              INTEGER NOT NULL REFERENCES patients(patient_id),
    assigned_coordinator_id INTEGER REFERENCES care_coordinators(coordinator_id),
    created_by_provider_id  INTEGER REFERENCES providers(provider_id),
    message_intent          TEXT,
    message                 TEXT,
    status                  TEXT DEFAULT 'OPEN',
    priority                TEXT DEFAULT 'NORMAL',
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT,
    completed_at            TEXT,
    completion_note         TEXT
);

CREATE TABLE IF NOT EXISTS outreach_attempts (
    attempt_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id     INTEGER NOT NULL REFERENCES patients(patient_id),
    coordinator_id INTEGER REFERENCES care_coordinators(coordinator_id),
    method         TEXT,
    outcome        TEXT,
    notes          TEXT,
    care_gap_id    INTEGER REFERENCES care_gaps(gap_id),
    attempt_time   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS engagement_events (
    event_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id       INTEGER NOT NULL REFERENCES patients(patient_id),
    coordinator_id   INTEGER REFERENCES care_coordinators(coordinator_id),
    event_type       TEXT,
    outcome          TEXT,
    event_timestamp  TEXT DEFAULT (datetime('now'))
);
"""

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()

def drop_all_tables():
    conn = get_connection()
    order = [
        "engagement_events", "outreach_attempts", "care_tasks",
        "patient_risk_profile", "care_gaps", "sdoh_assessment",
        "diagnoses", "procedures", "encounters",
        "patients", "measure_reference",
        "care_coordinators", "providers", "clinics",
    ]
    for t in order:
        conn.execute(f"DROP TABLE IF EXISTS {t}")
    conn.commit()
    conn.close()
