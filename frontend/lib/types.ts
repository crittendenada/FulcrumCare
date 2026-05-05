export type RiskBucket = "VERY_HIGH" | "HIGH" | "MEDIUM" | "LOW"

export interface Provider {
  provider_id: number
  name: string
  specialty: string
  clinic_id: number
  clinic_name: string
}

export interface Coordinator {
  coordinator_id: number
  name: string
  email: string
}

export interface Measure {
  measure_id: string
  name: string
  description: string
  category: string
  priority_weight: number
}

export interface Patient {
  patient_id: number
  first_name: string
  last_name: string
  age: number
  gender: string
  medicaid_id: string
  phone: string
  address: string
  city: string
  adi_decile: number
  is_diabetic: number
  has_hypertension: number
  has_periodontitis: number
  assigned_provider_id: number
  assigned_coordinator_id: number
  coordinator_id: number
  provider_name: string
  coordinator_name: string
  composite_risk: number
  risk_bucket: RiskBucket
  engagement_score: number
  clinical_score: number
  sdoh_score: number
}

export interface CareGap {
  gap_id: number
  gap_status: "OPEN" | "CLOSED" | "NOT_APPLICABLE"
  last_evaluated_at: string
  closed_at: string | null
  closed_by: string | null
  closure_note: string | null
  measure_id: string
  name: string
  description: string
  category: string
  priority_weight: number
}

export interface OutreachAttempt {
  attempt_id: number
  method: string
  outcome: string
  notes: string | null
  attempt_time: string
  coordinator_name: string
}

export interface CareTask {
  task_id: number
  message_intent: string
  message: string
  status: "OPEN" | "IN_PROGRESS" | "COMPLETED"
  created_at: string
  completed_at: string | null
  completion_note: string | null
  coordinator_name: string
  provider_name: string
}

export interface SdohAssessment {
  patient_id: number
  transportation: number
  communication_challenges: number
  cost_anxiety: number
  dental_fear: number
  work_schedule_constraints: number
  assessed_at: string
}

// ── Clinician panel response ───────────────────────────────────────────────

export interface PriorityPatient {
  patient_id: number
  first_name: string
  last_name: string
  age: number
  gender: string
  medicaid_id: string
  composite_risk: number
  risk_bucket: RiskBucket
  coordinator_name: string
  top_gap: string | null
  appt_scheduled: boolean
}

export interface ClinicianPanelData {
  measures_kpi: { measure_id: string; name: string; open_count: number }[]
  stats: { total: number; open_gap_patients: number; high_risk: number; ed_visits: number }
  priority_patients: PriorityPatient[]
  outreach_feed: {
    attempt_time: string; method: string; outcome: string
    notes: string | null; patient_name: string; patient_id: number; coordinator_name: string
  }[]
  task_feed: {
    completed_at: string; message_intent: string; completion_note: string | null
    patient_name: string; patient_id: number; coordinator_name: string
  }[]
}

export interface WorklistPatient {
  patient_id: number
  patient_name: string
  age: number
  gender: string
  medicaid_id: string
  gap_status: string
  risk_bucket: RiskBucket
  composite_risk: number
  coordinator_name: string
}

// ── Coordinator response ──────────────────────────────────────────────────

export interface CoordPatient {
  patient_id: number
  first_name: string
  last_name: string
  age: number
  gender: string
  medicaid_id: string
  adi_decile: number
  composite_risk: number
  risk_bucket: RiskBucket
  engagement_score: number
  clinical_score: number
  sdoh_score: number
  provider_name: string
  last_contact: string | null
  open_gap_count: number
}

export interface CoordPatientsData {
  kpis: { total: number; high_risk: number; open_tasks: number; outreach_this_week: number }
  patients: CoordPatient[]
}

// ── Admin responses ────────────────────────────────────────────────────────

export interface AdminStats {
  total: number
  open_gaps: number
  closed_gaps: number
  closure_rate: number
  high_risk: number
  diabetic_pct: number
  open_tasks: number
}

export interface GapByMeasure {
  measure: string
  OPEN?: number
  CLOSED?: number
}

export interface RiskDistItem {
  risk_bucket: RiskBucket
  count: number
}

export interface AdiItem {
  adi_decile: number
  total: number
  high_risk: number
}

export interface ComplianceItem {
  measure: string
  total: number
  closed: number
  pct: number
}

export interface ProviderPerfItem {
  provider: string
  clinic: string
  patients: number
  open_gaps: number
  closed_gaps: number
  closure_pct: number
  avg_risk: number
}

export interface OutreachSummaryItem {
  method: string
  attempts: number
  reached: number
  reach_rate: number
}

export interface DataQuality {
  sdoh_coverage: number
  risk_coverage: number
  gap_coverage: number
  engagement: { never_contacted: number; reached: number; appt_scheduled: number }
}
