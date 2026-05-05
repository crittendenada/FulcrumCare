"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { StatCard } from "@/components/StatCard"
import { MeasureBarChart } from "@/components/charts/MeasureBarChart"
import { RiskDonutChart } from "@/components/charts/RiskDonutChart"
import { ADIBarChart } from "@/components/charts/ADIBarChart"
import { ComplianceBarChart } from "@/components/charts/ComplianceBarChart"
import * as api from "@/lib/api"
import type { ProviderPerfItem, OutreachSummaryItem } from "@/lib/types"

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
      {children}
    </div>
  )
}

export default function AdminPage() {
  const [clinicId, setClinicId] = useState<number | undefined>(undefined)

  const { data: clinics = [] } = useQuery({
    queryKey: ["clinics"],
    queryFn: api.getClinics,
  })
  const { data: stats } = useQuery({
    queryKey: ["admin-stats", clinicId],
    queryFn: () => api.getAdminStats(clinicId),
  })
  const { data: gapsByMeasure = [] } = useQuery({
    queryKey: ["gaps-by-measure", clinicId],
    queryFn: () => api.getGapsByMeasure(clinicId),
  })
  const { data: riskDist = [] } = useQuery({
    queryKey: ["risk-dist", clinicId],
    queryFn: () => api.getRiskDistribution(clinicId),
  })
  const { data: adiDist = [] } = useQuery({
    queryKey: ["adi-dist", clinicId],
    queryFn: () => api.getAdiDistribution(clinicId),
  })
  const { data: compliance = [] } = useQuery({
    queryKey: ["compliance", clinicId],
    queryFn: () => api.getCompliance(clinicId),
  })
  const { data: providers = [] } = useQuery({
    queryKey: ["provider-perf"],
    queryFn: api.getProviderPerf,
  })
  const { data: outreachSummary = [] } = useQuery({
    queryKey: ["outreach-summary"],
    queryFn: api.getOutreachSummary,
  })
  const { data: dataQuality } = useQuery({
    queryKey: ["data-quality"],
    queryFn: api.getDataQuality,
  })

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 space-y-8">
      {/* Header + clinic filter */}
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Population Health</h1>
          <p className="text-sm text-gray-500">Panel-level analytics and care gap trends</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Clinic</label>
          <select
            value={clinicId ?? ""}
            onChange={e => setClinicId(e.target.value ? Number(e.target.value) : undefined)}
            className="rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-sm outline-none focus:border-brand"
          >
            <option value="">All Clinics</option>
            {clinics.map(c => (
              <option key={c.clinic_id} value={c.clinic_id}>{c.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {stats ? (
          <>
            <StatCard label="Total Patients"  value={stats.total} />
            <StatCard label="Open Gaps"       value={stats.open_gaps}      valueClassName="text-red-600" />
            <StatCard label="Closed Gaps"     value={stats.closed_gaps}    valueClassName="text-green-600" />
            <StatCard label="Closure Rate"    value={`${stats.closure_rate.toFixed(1)}%`} valueClassName="text-emerald-600" />
            <StatCard label="High+ Risk"      value={stats.high_risk}      valueClassName="text-orange-600" />
            <StatCard label="Diabetic %"      value={`${stats.diabetic_pct.toFixed(1)}%`} />
          </>
        ) : (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-gray-200 bg-white p-4 animate-pulse">
              <div className="h-3 bg-gray-200 rounded mb-3 w-2/3" />
              <div className="h-7 bg-gray-200 rounded w-1/2" />
            </div>
          ))
        )}
      </div>

      {/* Charts 2×2 */}
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Care Gaps by Measure">
          {gapsByMeasure.length > 0
            ? <MeasureBarChart data={gapsByMeasure} />
            : <p className="text-sm text-gray-400 py-8 text-center">No data</p>}
        </ChartCard>

        <ChartCard title="Risk Distribution">
          {riskDist.length > 0
            ? <RiskDonutChart data={riskDist} />
            : <p className="text-sm text-gray-400 py-8 text-center">No data</p>}
        </ChartCard>

        <ChartCard title="Social Risk by ADI Decile">
          {adiDist.length > 0
            ? <ADIBarChart data={adiDist} />
            : <p className="text-sm text-gray-400 py-8 text-center">No data</p>}
        </ChartCard>

        <ChartCard title="Gap Closure Rate by Measure">
          {compliance.length > 0
            ? <ComplianceBarChart data={compliance} />
            : <p className="text-sm text-gray-400 py-8 text-center">No data</p>}
        </ChartCard>
      </div>

      {/* Provider performance */}
      {providers.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">Provider Performance</h2>
          <div className="rounded-xl border border-gray-200 overflow-hidden bg-white">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs font-medium text-gray-500">
                <tr>
                  <th className="px-4 py-2.5 text-left">Provider</th>
                  <th className="px-4 py-2.5 text-left">Clinic</th>
                  <th className="px-4 py-2.5 text-right">Patients</th>
                  <th className="px-4 py-2.5 text-right">Open Gaps</th>
                  <th className="px-4 py-2.5 text-right">Closed Gaps</th>
                  <th className="px-4 py-2.5 text-right">Closure %</th>
                  <th className="px-4 py-2.5 text-right">Avg Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {providers.map((p: ProviderPerfItem) => (
                  <tr key={p.provider} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-medium text-gray-900">{p.provider}</td>
                    <td className="px-4 py-2.5 text-gray-500">{p.clinic}</td>
                    <td className="px-4 py-2.5 text-right text-gray-700">{p.patients}</td>
                    <td className="px-4 py-2.5 text-right text-red-600">{p.open_gaps}</td>
                    <td className="px-4 py-2.5 text-right text-green-600">{p.closed_gaps}</td>
                    <td className="px-4 py-2.5 text-right">
                      <span className={
                        p.closure_pct >= 60 ? "text-emerald-600 font-medium"
                          : p.closure_pct >= 35 ? "text-amber-600 font-medium"
                          : "text-red-600 font-medium"
                      }>
                        {p.closure_pct.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right text-gray-700">{p.avg_risk.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Outreach summary */}
        {outreachSummary.length > 0 && (
          <div>
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">Outreach Summary (30d)</h2>
            <div className="rounded-xl border border-gray-200 overflow-hidden bg-white">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs font-medium text-gray-500">
                  <tr>
                    <th className="px-4 py-2.5 text-left">Method</th>
                    <th className="px-4 py-2.5 text-right">Attempts</th>
                    <th className="px-4 py-2.5 text-right">Reached</th>
                    <th className="px-4 py-2.5 text-right">Reach Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {outreachSummary.map((o: OutreachSummaryItem) => (
                    <tr key={o.method} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5 font-medium text-gray-900">{o.method}</td>
                      <td className="px-4 py-2.5 text-right text-gray-700">{o.attempts}</td>
                      <td className="px-4 py-2.5 text-right text-gray-700">{o.reached}</td>
                      <td className="px-4 py-2.5 text-right">
                        <span className={o.reach_rate >= 50 ? "text-emerald-600 font-medium" : "text-amber-600 font-medium"}>
                          {o.reach_rate.toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Data quality */}
        {dataQuality && (
          <div>
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">Data Quality</h2>
            <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
              {[
                { label: "Risk Profile Coverage",  value: dataQuality.risk_coverage },
                { label: "Care Gap Coverage",       value: dataQuality.gap_coverage },
                { label: "SDOH Assessment Coverage", value: dataQuality.sdoh_coverage },
              ].map(({ label, value }) => (
                <div key={label}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-600">{label}</span>
                    <span className="font-medium text-gray-800">{value.toFixed(1)}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        value >= 80 ? "bg-emerald-500" : value >= 50 ? "bg-amber-400" : "bg-red-400"
                      }`}
                      style={{ width: `${value}%` }}
                    />
                  </div>
                </div>
              ))}

              <div className="pt-2 border-t border-gray-100">
                <p className="text-xs font-medium text-gray-500 mb-2">Engagement Breakdown</p>
                <div className="grid grid-cols-3 gap-2">
                  <div className="text-center">
                    <p className="text-lg font-bold text-red-600">{dataQuality.engagement.never_contacted}</p>
                    <p className="text-xs text-gray-400">Never Contacted</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-bold text-brand">{dataQuality.engagement.reached}</p>
                    <p className="text-xs text-gray-400">Reached</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-bold text-emerald-600">{dataQuality.engagement.appt_scheduled}</p>
                    <p className="text-xs text-gray-400">Appt Scheduled</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
