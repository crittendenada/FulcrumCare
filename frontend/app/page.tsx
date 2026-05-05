"use client"

import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import { Stethoscope, Users, BarChart3, ArrowRight, TrendingDown, Activity } from "lucide-react"
import * as api from "@/lib/api"

const ROLES = [
  {
    href: "/clinician",
    icon: Stethoscope,
    label: "Clinician",
    title: "Patient Panel & Worklist",
    desc: "See your priority patients ranked by risk, review open care gaps, and notify care coordinators — all from one view.",
    accent: "border-brand-200 hover:border-brand hover:bg-brand-50",
    iconBg: "bg-brand-50",
    iconColor: "text-brand",
    cta: "Enter Clinician View",
  },
  {
    href: "/coordinator",
    icon: Users,
    label: "Care Coordinator",
    title: "Caseload & Outreach",
    desc: "Manage your assigned patients, log outreach attempts, and track open care tasks from providers.",
    accent: "border-[#94C8D9]/40 hover:border-teal hover:bg-teal-50",
    iconBg: "bg-teal-50",
    iconColor: "text-[#2B8EA6]",
    cta: "Enter Coordinator View",
  },
  {
    href: "/admin",
    icon: BarChart3,
    label: "Population Health",
    title: "Dashboard & Analytics",
    desc: "Monitor care gap closure rates, risk distribution, ADI-driven social risk, and provider performance across the panel.",
    accent: "border-[#FAAD9A]/40 hover:border-coral hover:bg-coral-50",
    iconBg: "bg-coral-50",
    iconColor: "text-[#C45C3A]",
    cta: "Enter Admin View",
  },
]

const VALUE_PROPS = [
  {
    icon: TrendingDown,
    stat: "~$2,400",
    label: "est. downstream savings per high-risk patient",
    color: "text-brand",
  },
  {
    icon: Activity,
    stat: "3–5×",
    label: "higher closure rates with coordinated outreach",
    color: "text-[#2B8EA6]",
  },
]

export default function HomePage() {
  const { data: stats } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: () => api.getAdminStats(),
  })

  return (
    <div className="mx-auto max-w-3xl px-8 py-12 space-y-12">

      {/* Hero */}
      <div className="space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-semibold text-brand">
          Live Demo · Hillhouse Community Health Center, New Haven, CT
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-navy leading-tight">
          Preventive dental care coordination<br />
          <span className="text-brand">for Medicaid & Medicare populations</span>
        </h1>
        <p className="text-base text-[#565150] max-w-xl leading-relaxed">
          FulcrumCare connects oral health interventions to downstream medical savings —
          reducing ED visits, improving A1c control, and lowering total cost of care for
          payers and health systems.
        </p>
      </div>

      {/* Live panel stats */}
      {stats && (
        <div className="rounded-2xl border border-gray-200 bg-white p-6">
          <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-4">
            Live Panel — Hillhouse CHC
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            <div>
              <p className="text-3xl font-bold text-gray-900">{stats.total}</p>
              <p className="text-xs text-gray-500 mt-0.5">Total patients</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-orange-600">{stats.high_risk}</p>
              <p className="text-xs text-gray-500 mt-0.5">High / very high risk</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-red-600">{stats.open_gaps}</p>
              <p className="text-xs text-gray-500 mt-0.5">Open care gaps</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-emerald-600">{stats.closure_rate.toFixed(1)}%</p>
              <p className="text-xs text-gray-500 mt-0.5">Gap closure rate</p>
            </div>
          </div>
        </div>
      )}

      {/* Role entry points */}
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">
          Explore the Demo
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          {ROLES.map(({ href, icon: Icon, title, desc, accent, iconBg, iconColor, cta }) => (
            <Link
              key={href}
              href={href}
              className={`group rounded-xl border-2 bg-white p-5 transition-all space-y-3 ${accent}`}
            >
              <div className={`w-9 h-9 rounded-lg ${iconBg} flex items-center justify-center`}>
                <Icon className={`h-4.5 w-4.5 ${iconColor}`} />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 text-sm">{title}</h3>
                <p className="text-xs text-gray-500 mt-1 leading-relaxed">{desc}</p>
              </div>
              <div className="flex items-center gap-1 text-xs font-medium text-gray-400 group-hover:text-gray-700 transition-colors">
                {cta}
                <ArrowRight className="h-3 w-3" />
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Value props */}
      <div className="grid gap-4 sm:grid-cols-2">
        {VALUE_PROPS.map(({ icon: Icon, stat, label, color }) => (
          <div key={stat} className="rounded-xl border border-gray-200 bg-white px-5 py-4 flex items-center gap-4">
            <div className="rounded-lg bg-gray-50 p-2.5">
              <Icon className={`h-5 w-5 ${color}`} />
            </div>
            <div>
              <p className={`text-2xl font-bold ${color}`}>{stat}</p>
              <p className="text-xs text-gray-500 mt-0.5">{label}</p>
            </div>
          </div>
        ))}
      </div>

    </div>
  )
}
