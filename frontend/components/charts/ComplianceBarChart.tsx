"use client"

import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, CartesianGrid,
} from "recharts"
import type { ComplianceItem } from "@/lib/types"

interface Props {
  data: ComplianceItem[]
}

const shorten = (name: string) =>
  name.length > 22 ? name.slice(0, 20) + "…" : name

export function ComplianceBarChart({ data }: Props) {
  const formatted = data.map(d => ({
    ...d,
    measure: shorten(d.measure),
    pct: Math.round(d.pct),
  }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart
        data={formatted}
        layout="vertical"
        margin={{ top: 4, right: 40, bottom: 4, left: 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e9e8e7" horizontal={false} />
        <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
        <YAxis dataKey="measure" type="category" tick={{ fontSize: 11 }} width={130} />
        <Tooltip
          contentStyle={{ fontSize: 12 }}
          formatter={(v) => [`${v}%`, "Closure Rate"]}
        />
        <Bar dataKey="pct" name="Closure %" radius={[0, 4, 4, 0]}>
          {formatted.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.pct >= 70 ? "#79ADBD" : entry.pct >= 40 ? "#FAAD9A" : "#f8712e"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
