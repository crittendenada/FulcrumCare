"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { StatCard } from "@/components/StatCard"
import { RiskBadge, RISK_SCORE_COLOR } from "@/components/RiskBadge"
import { CareGapCard } from "@/components/CareGapCard"
import { LogOutreachForm } from "@/components/LogOutreachForm"
import * as api from "@/lib/api"
import type { CoordPatient } from "@/lib/types"
import { cn } from "@/lib/utils"

function fmt(dt: string | null) {
  if (!dt) return "Never"
  return new Date(dt).toLocaleDateString(undefined, { month: "short", day: "numeric" })
}

// ─── Patient Workup ────────────────────────────────────────────────────────────

function PatientWorkup({ patientId, coordinatorId }: { patientId: number; coordinatorId: number }) {
  const qc = useQueryClient()

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

  const completeTask = useMutation({
    mutationFn: ({ taskId }: { taskId: number }) =>
      api.completeTask(taskId, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks", patientId] })
      toast.success("Task marked complete")
    },
    onError: () => toast.error("Failed to complete task"),
  })

  if (!patient) return <p className="text-sm text-gray-400 py-8 text-center">Loading…</p>

  const openGaps = gaps.filter(g => g.gap_status === "OPEN")
  const openTasks = tasks.filter(t => t.status !== "COMPLETED")

  return (
    <div className="space-y-6">
      {/* Patient header */}
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
          <p className="text-xs text-gray-400 mt-1">Provider: {patient.provider_name}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <RiskBadge bucket={patient.risk_bucket} score={patient.composite_risk} />
          <p className="text-xs text-gray-400">
            Eng {patient.engagement_score.toFixed(0)} · Clin {patient.clinical_score.toFixed(0)} · SDOH {patient.sdoh_score.toFixed(0)}
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Open tasks */}
        <div>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">
            Open Tasks ({openTasks.length})
          </h3>
          <div className="space-y-2">
            {openTasks.length === 0 && (
              <p className="text-sm text-gray-400">No open tasks.</p>
            )}
            {openTasks.map(t => (
              <div key={t.task_id} className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{t.message_intent}</p>
                    <p className="text-xs text-gray-600 mt-0.5">{t.message}</p>
                    <p className="text-xs text-gray-400 mt-1">From {t.provider_name} · {fmt(t.created_at)}</p>
                  </div>
                  <button
                    onClick={() => completeTask.mutate({ taskId: t.task_id })}
                    disabled={completeTask.isPending}
                    className="shrink-0 text-xs rounded-lg border border-green-300 bg-white px-2 py-1 text-green-700 hover:bg-green-50 transition-colors disabled:opacity-50"
                  >
                    Mark Done
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Open care gaps */}
          {openGaps.length > 0 && (
            <div className="mt-4">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">
                Open Care Gaps ({openGaps.length})
              </h3>
              <div className="space-y-2">
                {openGaps.map(g => (
                  <CareGapCard key={g.gap_id} gap={g} patientId={patientId} closedBy="Coordinator" />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Log outreach + history */}
        <div className="space-y-4">
          <div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">Log Outreach</h3>
            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <LogOutreachForm
                patientId={patientId}
                coordinatorId={coordinatorId}
                openGaps={openGaps}
              />
            </div>
          </div>

          {outreach.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">Outreach History</h3>
              <div className="divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white">
                {outreach.map(o => (
                  <div key={o.attempt_id} className="px-4 py-2.5 flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm text-gray-800">
                        <span className="font-medium">{o.method}</span> · {o.outcome}
                      </p>
                      {o.notes && <p className="text-xs text-gray-500 mt-0.5">{o.notes}</p>}
                    </div>
                    <span className="text-xs text-gray-400 shrink-0">{fmt(o.attempt_time)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Main page ─────────────────────────────────────────────────────────────────

export default function CoordinatorPage() {
  const [tab, setTab]                       = useState("patients")
  const [coordinatorId, setCoordinatorId]   = useState<number>(0)
  const [selectedPatientId, setSelectedPatientId] = useState<number | null>(null)

  const { data: coordinators = [] } = useQuery({
    queryKey: ["coordinators"],
    queryFn: api.getCoordinators,
  })

  const { data: coordData } = useQuery({
    queryKey: ["coord-patients", coordinatorId],
    queryFn: () => api.getCoordPatients(coordinatorId),
    enabled: !!coordinatorId,
  })

  function selectPatient(id: number) {
    setSelectedPatientId(id)
    setTab("workup")
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8 space-y-6">
      {/* Header + coordinator selector */}
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Care Coordinator</h1>
          <p className="text-sm text-gray-500">Caseload management, outreach logging, and task tracking</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Coordinator</label>
          <select
            value={coordinatorId}
            onChange={e => setCoordinatorId(Number(e.target.value))}
            className="rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-sm outline-none focus:border-brand"
          >
            <option value={0}>Select coordinator…</option>
            {coordinators.map(c => (
              <option key={c.coordinator_id} value={c.coordinator_id}>{c.name}</option>
            ))}
          </select>
        </div>
      </div>

      {!coordinatorId && (
        <div className="rounded-xl border border-dashed border-gray-300 py-16 text-center text-gray-400">
          Select a coordinator to load their patient caseload.
        </div>
      )}

      {!!coordinatorId && (
        <Tabs value={tab} onValueChange={(v) => setTab(String(v))}>
          <TabsList variant="line">
            <TabsTrigger value="patients">My Patients</TabsTrigger>
            <TabsTrigger value="workup" disabled={!selectedPatientId}>
              Patient Workup{selectedPatientId ? "" : " (select a patient)"}
            </TabsTrigger>
          </TabsList>

          {/* ── My Patients ── */}
          <TabsContent value="patients" className="space-y-5 mt-4">
            {coordData && (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <StatCard label="Total Assigned"     value={coordData.kpis.total} />
                  <StatCard label="High+ Risk"         value={coordData.kpis.high_risk} valueClassName="text-orange-600" />
                  <StatCard label="Open Tasks"         value={coordData.kpis.open_tasks} valueClassName="text-amber-600" />
                  <StatCard label="Outreach This Week" value={coordData.kpis.outreach_this_week} valueClassName="text-brand" />
                </div>

                <div className="rounded-xl border border-gray-200 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 text-xs font-medium text-gray-500">
                      <tr>
                        <th className="px-4 py-2.5 text-left">Patient</th>
                        <th className="px-4 py-2.5 text-left">Risk Score</th>
                        <th className="px-4 py-2.5 text-left">Open Gaps</th>
                        <th className="px-4 py-2.5 text-left">Last Contact</th>
                        <th className="px-4 py-2.5 text-left">Provider</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {coordData.patients.map((p: CoordPatient) => (
                        <tr
                          key={p.patient_id}
                          className="hover:bg-brand-50 cursor-pointer transition-colors"
                          onClick={() => selectPatient(p.patient_id)}
                        >
                          <td className="px-4 py-2.5">
                            <p className="font-medium text-gray-900">{p.first_name} {p.last_name}</p>
                            <p className="text-xs text-gray-400">{p.age}y {p.gender} · ADI {p.adi_decile}</p>
                          </td>
                          <td className="px-4 py-2.5">
                            <RiskBadge bucket={p.risk_bucket} score={p.composite_risk} />
                          </td>
                          <td className="px-4 py-2.5">
                            <span className={cn(
                              "text-sm font-semibold",
                              p.open_gap_count > 0 ? "text-red-600" : "text-gray-400"
                            )}>
                              {p.open_gap_count}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-xs text-gray-500">{fmt(p.last_contact)}</td>
                          <td className="px-4 py-2.5 text-xs text-gray-500">{p.provider_name}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
            {!coordData && (
              <p className="text-sm text-gray-400 py-8 text-center">Loading caseload…</p>
            )}
          </TabsContent>

          {/* ── Workup ── */}
          <TabsContent value="workup" className="mt-4">
            {selectedPatientId ? (
              <PatientWorkup patientId={selectedPatientId} coordinatorId={coordinatorId} />
            ) : (
              <p className="text-sm text-gray-400 py-8 text-center">
                Select a patient from My Patients to open their workup.
              </p>
            )}
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
