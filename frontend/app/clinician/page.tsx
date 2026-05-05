"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { StatCard } from "@/components/StatCard"
import { RiskBadge, RISK_SCORE_COLOR } from "@/components/RiskBadge"
import { CareGapCard } from "@/components/CareGapCard"
import { NotifyCoordDialog } from "@/components/NotifyCoordDialog"
import * as api from "@/lib/api"
import type { PriorityPatient, WorklistPatient } from "@/lib/types"
import { cn } from "@/lib/utils"

// ─── helpers ──────────────────────────────────────────────────────────────────

function fmt(dt: string) {
  return new Date(dt).toLocaleDateString(undefined, { month: "short", day: "numeric" })
}

// ─── Patient Record panel ──────────────────────────────────────────────────────

function PatientRecord({ patientId, providerId }: { patientId: number; providerId: number }) {
  const { data: patient } = useQuery({
    queryKey: ["patient", patientId],
    queryFn: () => api.getPatient(patientId),
    enabled: !!patientId,
  })
  const { data: gaps = [] } = useQuery({
    queryKey: ["gaps", patientId],
    queryFn: () => api.getPatientGaps(patientId),
    enabled: !!patientId,
  })
  const { data: tasks = [] } = useQuery({
    queryKey: ["tasks", patientId],
    queryFn: () => api.getPatientTasks(patientId),
    enabled: !!patientId,
  })
  const { data: outreach = [] } = useQuery({
    queryKey: ["outreach", patientId],
    queryFn: () => api.getPatientOutreach(patientId),
    enabled: !!patientId,
  })
  const { data: sdoh } = useQuery({
    queryKey: ["sdoh", patientId],
    queryFn: () => api.getPatientSdoh(patientId),
    enabled: !!patientId,
  })

  if (!patient) return <p className="text-sm text-gray-400 py-8 text-center">Loading patient record…</p>

  const sdohFlags = sdoh && "transportation" in sdoh
    ? (Object.entries(sdoh) as [string, number | string][])
        .filter(([k, v]) => k !== "patient_id" && k !== "assessed_at" && v === 1)
        .map(([k]) => k.replace(/_/g, " "))
    : []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">
            {patient.first_name} {patient.last_name}
          </h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {patient.age}y {patient.gender} · Medicaid ID {patient.medicaid_id}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {patient.city} · ADI Decile {patient.adi_decile}
            {patient.is_diabetic ? " · Diabetic" : ""}
            {patient.has_hypertension ? " · HTN" : ""}
            {patient.has_periodontitis ? " · Periodontitis" : ""}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Provider: {patient.provider_name} · Coordinator: {patient.coordinator_name}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <RiskBadge bucket={patient.risk_bucket} score={patient.composite_risk} />
          <p className="text-xs text-gray-400">
            Eng {patient.engagement_score.toFixed(0)} · Clin {patient.clinical_score.toFixed(0)} · SDOH {patient.sdoh_score.toFixed(0)}
          </p>
          <NotifyCoordDialog
            patientId={patient.patient_id}
            providerId={providerId}
            patientName={`${patient.first_name} ${patient.last_name}`}
          />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Care Gaps */}
        <div>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">
            Care Gaps ({gaps.filter(g => g.gap_status === "OPEN").length} open)
          </h3>
          <div className="space-y-2">
            {gaps.length === 0 && <p className="text-sm text-gray-400">No care gaps found.</p>}
            {gaps.map(g => (
              <CareGapCard key={g.gap_id} gap={g} patientId={patientId} closedBy={`Provider ${providerId}`} />
            ))}
          </div>
        </div>

        {/* Tasks */}
        <div>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">
            Care Tasks
          </h3>
          <div className="space-y-2">
            {tasks.length === 0 && <p className="text-sm text-gray-400">No tasks.</p>}
            {tasks.map(t => (
              <div key={t.task_id} className="rounded-lg border border-gray-200 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{t.message_intent}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{t.message}</p>
                  </div>
                  <span className={cn(
                    "text-xs px-2 py-0.5 rounded-full border",
                    t.status === "COMPLETED" ? "bg-green-50 border-green-200 text-green-700"
                      : t.status === "IN_PROGRESS" ? "bg-brand-50 border-brand-200 text-brand"
                      : "bg-amber-50 border-amber-200 text-amber-700"
                  )}>{t.status}</span>
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  {t.coordinator_name} · {fmt(t.created_at)}
                </p>
              </div>
            ))}
          </div>

          {/* SDOH */}
          {sdohFlags.length > 0 && (
            <div className="mt-4">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">SDOH Barriers</h3>
              <div className="flex flex-wrap gap-1.5">
                {sdohFlags.map(f => (
                  <span key={f} className="text-xs bg-purple-50 border border-purple-200 text-purple-700 px-2 py-0.5 rounded-full capitalize">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Outreach History */}
      {outreach.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">
            Recent Outreach
          </h3>
          <div className="divide-y divide-gray-100 rounded-xl border border-gray-200">
            {outreach.map(o => (
              <div key={o.attempt_id} className="px-4 py-2.5 flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm text-gray-800">
                    <span className="font-medium">{o.method}</span> · {o.outcome}
                  </p>
                  {o.notes && <p className="text-xs text-gray-500 mt-0.5">{o.notes}</p>}
                </div>
                <span className="text-xs text-gray-400 shrink-0">{fmt(o.attempt_time)} · {o.coordinator_name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Worklist tab ──────────────────────────────────────────────────────────────

function WorklistTab({
  providerId,
  onSelectPatient,
}: {
  providerId: number
  onSelectPatient: (id: number) => void
}) {
  const { data: panel } = useQuery({
    queryKey: ["panel", providerId],
    queryFn: () => api.getClinicianPanel(providerId),
    enabled: !!providerId,
  })
  const [measureId, setMeasureId] = useState<string>("")

  const { data: worklist = [], isFetching } = useQuery({
    queryKey: ["worklist", providerId, measureId],
    queryFn: () => api.getWorklist(providerId, measureId),
    enabled: !!providerId && !!measureId,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700 shrink-0">Measure</label>
        <select
          value={measureId}
          onChange={e => setMeasureId(e.target.value)}
          className="rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-sm outline-none focus:border-brand"
        >
          <option value="">Select a measure…</option>
          {panel?.measures_kpi.map(m => (
            <option key={m.measure_id} value={m.measure_id}>
              {m.name} ({m.open_count} open)
            </option>
          ))}
        </select>
      </div>

      {!measureId && (
        <p className="text-sm text-gray-400 py-6 text-center">Select a measure to see your patient worklist.</p>
      )}

      {measureId && (
        <div className="rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs font-medium text-gray-500">
              <tr>
                <th className="px-4 py-2.5 text-left">Patient</th>
                <th className="px-4 py-2.5 text-left">Gap Status</th>
                <th className="px-4 py-2.5 text-left">Risk</th>
                <th className="px-4 py-2.5 text-left">Coordinator</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isFetching && (
                <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400">Loading…</td></tr>
              )}
              {!isFetching && worklist.length === 0 && (
                <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400">No patients for this measure.</td></tr>
              )}
              {worklist.map((p: WorklistPatient) => (
                <tr
                  key={p.patient_id}
                  className="hover:bg-brand-50 cursor-pointer transition-colors"
                  onClick={() => onSelectPatient(p.patient_id)}
                >
                  <td className="px-4 py-2.5">
                    <p className="font-medium text-gray-900">{p.patient_name}</p>
                    <p className="text-xs text-gray-400">{p.age}y {p.gender} · {p.medicaid_id}</p>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={cn(
                      "text-xs px-2 py-0.5 rounded-full border",
                      p.gap_status === "OPEN" ? "bg-red-50 border-red-200 text-red-700" : "bg-green-50 border-green-200 text-green-700"
                    )}>{p.gap_status}</span>
                  </td>
                  <td className="px-4 py-2.5">
                    <RiskBadge bucket={p.risk_bucket} score={p.composite_risk} />
                  </td>
                  <td className="px-4 py-2.5 text-gray-500 text-xs">{p.coordinator_name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ─── Main page ─────────────────────────────────────────────────────────────────

export default function ClinicianPage() {
  const [tab, setTab] = useState("panel")
  const [providerId, setProviderId] = useState<number>(0)
  const [selectedPatientId, setSelectedPatientId] = useState<number | null>(null)

  const { data: providers = [] } = useQuery({
    queryKey: ["providers"],
    queryFn: api.getProviders,
  })

  const { data: panel } = useQuery({
    queryKey: ["panel", providerId],
    queryFn: () => api.getClinicianPanel(providerId),
    enabled: !!providerId,
  })

  function selectPatient(id: number) {
    setSelectedPatientId(id)
    setTab("record")
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8 space-y-6">
      {/* Header + provider selector */}
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clinician Dashboard</h1>
          <p className="text-sm text-gray-500">Patient panel, worklist, and full record view</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Provider</label>
          <select
            value={providerId}
            onChange={e => setProviderId(Number(e.target.value))}
            className="rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-sm outline-none focus:border-brand"
          >
            <option value={0}>Select provider…</option>
            {providers.map(p => (
              <option key={p.provider_id} value={p.provider_id}>
                {p.name} — {p.clinic_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {!providerId && (
        <div className="rounded-xl border border-dashed border-gray-300 py-16 text-center text-gray-400">
          Select a provider to load their patient panel.
        </div>
      )}

      {!!providerId && (
        <Tabs value={tab} onValueChange={(v) => setTab(String(v))}>
          <TabsList variant="line">
            <TabsTrigger value="panel">Patient Panel</TabsTrigger>
            <TabsTrigger value="worklist">Worklist</TabsTrigger>
            <TabsTrigger value="record" disabled={!selectedPatientId}>
              Patient Record{selectedPatientId ? "" : " (select a patient)"}
            </TabsTrigger>
          </TabsList>

          {/* ── Panel ── */}
          <TabsContent value="panel" className="space-y-6 mt-4">
            {!panel && (
              <div className="space-y-4 animate-pulse">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="rounded-xl border border-gray-200 bg-white p-4">
                      <div className="h-3 bg-gray-200 rounded mb-3 w-2/3" />
                      <div className="h-7 bg-gray-200 rounded w-1/2" />
                    </div>
                  ))}
                </div>
                <div className="rounded-xl border border-gray-200 bg-white p-4 h-48" />
              </div>
            )}
            {panel && (
              <>
                {/* KPI row */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <StatCard label="Panel Size"      value={panel.stats.total} />
                  <StatCard label="Open Gap Pts"    value={panel.stats.open_gap_patients} valueClassName="text-red-600" />
                  <StatCard label="High+ Risk"      value={panel.stats.high_risk} valueClassName="text-orange-600" />
                  <StatCard label="ED Visits (30d)" value={panel.stats.ed_visits} />
                </div>

                {/* Measures KPI */}
                <div>
                  <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">Open Gaps by Measure</h3>
                  <div className="flex flex-wrap gap-2">
                    {panel.measures_kpi.map(m => (
                      <div key={m.measure_id} className="rounded-lg border border-gray-200 bg-white px-3 py-2">
                        <p className="text-xs text-gray-500">{m.name}</p>
                        <p className="text-xl font-bold text-red-600">{m.open_count}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Priority patients */}
                <div>
                  <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">
                    Priority Patients ({panel.priority_patients.length})
                  </h3>
                  <div className="rounded-xl border border-gray-200 overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 text-xs font-medium text-gray-500">
                        <tr>
                          <th className="px-4 py-2.5 text-left">Patient</th>
                          <th className="px-4 py-2.5 text-left">Risk</th>
                          <th className="px-4 py-2.5 text-left">Top Gap</th>
                          <th className="px-4 py-2.5 text-left">Coordinator</th>
                          <th className="px-4 py-2.5 text-left">Appt</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {panel.priority_patients.map((p: PriorityPatient) => (
                          <tr
                            key={p.patient_id}
                            className="hover:bg-brand-50 cursor-pointer transition-colors"
                            onClick={() => selectPatient(p.patient_id)}
                          >
                            <td className="px-4 py-2.5">
                              <p className="font-medium text-gray-900">{p.first_name} {p.last_name}</p>
                              <p className="text-xs text-gray-400">{p.age}y {p.gender}</p>
                            </td>
                            <td className="px-4 py-2.5">
                              <RiskBadge bucket={p.risk_bucket} score={p.composite_risk} />
                            </td>
                            <td className="px-4 py-2.5 text-xs text-gray-500 max-w-[180px] truncate">
                              {p.top_gap ?? "—"}
                            </td>
                            <td className="px-4 py-2.5 text-xs text-gray-500">{p.coordinator_name}</td>
                            <td className="px-4 py-2.5 text-xs">
                              {p.appt_scheduled
                                ? <span className="text-green-600">✓ Scheduled</span>
                                : <span className="text-gray-400">—</span>}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Activity feed */}
                {(panel.outreach_feed.length > 0 || panel.task_feed.length > 0) && (
                  <div className="grid gap-4 lg:grid-cols-2">
                    {panel.outreach_feed.length > 0 && (
                      <div>
                        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">Recent Outreach (14d)</h3>
                        <div className="space-y-1.5">
                          {panel.outreach_feed.slice(0, 5).map((o, i) => (
                            <div
                              key={i}
                              className="flex items-start justify-between gap-2 rounded-lg border border-gray-100 bg-white px-3 py-2 cursor-pointer hover:border-brand-200"
                              onClick={() => selectPatient(o.patient_id)}
                            >
                              <div>
                                <p className="text-xs font-medium text-gray-800">{o.patient_name}</p>
                                <p className="text-xs text-gray-500">{o.method} · {o.outcome}</p>
                              </div>
                              <span className="text-xs text-gray-400 shrink-0">{fmt(o.attempt_time)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {panel.task_feed.length > 0 && (
                      <div>
                        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">Completed Tasks (14d)</h3>
                        <div className="space-y-1.5">
                          {panel.task_feed.slice(0, 5).map((t, i) => (
                            <div
                              key={i}
                              className="flex items-start justify-between gap-2 rounded-lg border border-gray-100 bg-white px-3 py-2 cursor-pointer hover:border-brand-200"
                              onClick={() => selectPatient(t.patient_id)}
                            >
                              <div>
                                <p className="text-xs font-medium text-gray-800">{t.patient_name}</p>
                                <p className="text-xs text-gray-500">{t.message_intent}</p>
                              </div>
                              <span className="text-xs text-gray-400 shrink-0">{fmt(t.completed_at)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
            {!panel && (
              <p className="text-sm text-gray-400 py-8 text-center">Loading panel data…</p>
            )}
          </TabsContent>

          {/* ── Worklist ── */}
          <TabsContent value="worklist" className="mt-4">
            <WorklistTab providerId={providerId} onSelectPatient={selectPatient} />
          </TabsContent>

          {/* ── Record ── */}
          <TabsContent value="record" className="mt-4">
            {selectedPatientId ? (
              <PatientRecord patientId={selectedPatientId} providerId={providerId} />
            ) : (
              <p className="text-sm text-gray-400 py-8 text-center">
                Click a patient from the Panel or Worklist to view their record.
              </p>
            )}
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
