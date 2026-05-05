import type {
  Provider, Coordinator, Measure,
  Patient, CareGap, OutreachAttempt, CareTask, SdohAssessment,
  ClinicianPanelData, WorklistPatient,
  CoordPatientsData,
  AdminStats, GapByMeasure, RiskDistItem, AdiItem,
  ComplianceItem, ProviderPerfItem, OutreachSummaryItem, DataQuality,
} from "@/lib/types"

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" })
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

// ── Lookups ────────────────────────────────────────────────────────────────
export const getProviders   = () => get<Provider[]>("/api/providers")
export const getCoordinators = () => get<Coordinator[]>("/api/coordinators")
export const getMeasures    = () => get<Measure[]>("/api/measures")
export const getClinics     = () => get<{ clinic_id: number; name: string }[]>("/api/admin/clinics")

// ── Patient detail ─────────────────────────────────────────────────────────
export const getPatient     = (id: number) => get<Patient>(`/api/patients/${id}`)
export const getPatientGaps = (id: number) => get<CareGap[]>(`/api/patients/${id}/gaps`)
export const getPatientOutreach = (id: number) => get<OutreachAttempt[]>(`/api/patients/${id}/outreach`)
export const getPatientTasks = (id: number) => get<CareTask[]>(`/api/patients/${id}/tasks`)
export const getPatientSdoh = (id: number) => get<SdohAssessment | Record<string, never>>(`/api/patients/${id}/sdoh`)

// ── Patient actions ────────────────────────────────────────────────────────
export const closeGap = (gapId: number, body: { closed_by: string; closure_note?: string }) =>
  patch<{ ok: boolean }>(`/api/gaps/${gapId}/close`, body)

export const completeTask = (taskId: number, body: { completion_note?: string }) =>
  patch<{ ok: boolean }>(`/api/tasks/${taskId}/complete`, body)

// ── Clinician ──────────────────────────────────────────────────────────────
export const getClinicianPanel = (providerId: number) =>
  get<ClinicianPanelData>(`/api/clinician/${providerId}/panel`)

export const getWorklist = (providerId: number, measureId: string) =>
  get<WorklistPatient[]>(`/api/clinician/${providerId}/worklist?measure_id=${measureId}`)

export const createTask = (body: {
  patient_id: number
  coordinator_id: number
  provider_id: number
  intent: string
  message: string
}) => post<{ ok: boolean }>("/api/clinician/tasks", body)

// ── Coordinator ────────────────────────────────────────────────────────────
export const getCoordPatients = (coordinatorId: number) =>
  get<CoordPatientsData>(`/api/coordinator/${coordinatorId}/patients`)

export const logOutreach = (body: {
  patient_id: number
  coordinator_id: number
  method: string
  outcome: string
  notes?: string | null
  care_gap_id?: number | null
}) => post<{ ok: boolean }>("/api/coordinator/outreach", body)

// ── Admin ──────────────────────────────────────────────────────────────────
export const getAdminStats       = (clinicId?: number) => get<AdminStats>(`/api/admin/stats${clinicId ? `?clinic_id=${clinicId}` : ""}`)
export const getGapsByMeasure    = (clinicId?: number) => get<GapByMeasure[]>(`/api/admin/gaps-by-measure${clinicId ? `?clinic_id=${clinicId}` : ""}`)
export const getRiskDistribution = (clinicId?: number) => get<RiskDistItem[]>(`/api/admin/risk-distribution${clinicId ? `?clinic_id=${clinicId}` : ""}`)
export const getAdiDistribution  = (clinicId?: number) => get<AdiItem[]>(`/api/admin/adi-distribution${clinicId ? `?clinic_id=${clinicId}` : ""}`)
export const getCompliance       = (clinicId?: number) => get<ComplianceItem[]>(`/api/admin/compliance${clinicId ? `?clinic_id=${clinicId}` : ""}`)
export const getProviderPerf     = () => get<ProviderPerfItem[]>("/api/admin/providers")
export const getOutreachSummary  = () => get<OutreachSummaryItem[]>("/api/admin/outreach-summary")
export const getDataQuality      = () => get<DataQuality>("/api/admin/data-quality")

// ── Seed ──────────────────────────────────────────────────────────────────
export const seedDatabase = () => post<{ ok: boolean }>("/api/seed", {})
