"use client"

import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from "recharts"
import type { RiskDistItem } from "@/lib/types"

interface Props {
  data: RiskDistItem[]
}

const COLORS: Record<string, string> = {
  VERY_HIGH: "#f8712e",
  HIGH:      "#FAAD9A",
  MEDIUM:    "#79ADBD",
  LOW:       "#9cd5e7",
}

const LABELS: Record<string, string> = {
  VERY_HIGH: "Very High",
  HIGH:      "High",
  MEDIUM:    "Moderate",
  LOW:       "Low",
}

const ORDER = ["VERY_HIGH", "HIGH", "MEDIUM", "LOW"]

export function RiskDonutChart({ data }: Props) {
  const sorted = ORDER
    .map(bucket => data.find(d => d.risk_bucket === bucket))
    .filter(Boolean)
    .map(d => ({ name: LABELS[d!.risk_bucket], value: d!.count, bucket: d!.risk_bucket }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={sorted}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={95}
          paddingAngle={2}
        >
          {sorted.map((entry) => (
            <Cell key={entry.bucket} fill={COLORS[entry.bucket]} />
          ))}
        </Pie>
        <Tooltip contentStyle={{ fontSize: 12 }} formatter={(v) => [v, "Patients"]} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  )
}
