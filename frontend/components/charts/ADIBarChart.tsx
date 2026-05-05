"use client"

import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid,
} from "recharts"
import type { AdiItem } from "@/lib/types"

interface Props {
  data: AdiItem[]
}

export function ADIBarChart({ data }: Props) {
  const sorted = [...data].sort((a, b) => a.adi_decile - b.adi_decile)

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={sorted} margin={{ top: 4, right: 8, bottom: 16, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e9e8e7" />
        <XAxis dataKey="adi_decile" tick={{ fontSize: 11 }} label={{ value: "ADI Decile", position: "insideBottom", offset: -8, fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
        <Tooltip contentStyle={{ fontSize: 12 }} />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
        <Bar dataKey="total"     name="Total"     fill="#0416A2" radius={[2, 2, 0, 0]} />
        <Bar dataKey="high_risk" name="High Risk"  fill="#FAAD9A" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
