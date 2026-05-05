"use client"

import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid,
} from "recharts"
import type { GapByMeasure } from "@/lib/types"

interface Props {
  data: GapByMeasure[]
}

const shorten = (name: string) =>
  name.length > 20 ? name.slice(0, 18) + "…" : name

export function MeasureBarChart({ data }: Props) {
  const formatted = data.map(d => ({ ...d, measure: shorten(d.measure) }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={formatted} margin={{ top: 4, right: 8, bottom: 40, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e9e8e7" />
        <XAxis
          dataKey="measure"
          tick={{ fontSize: 11 }}
          angle={-30}
          textAnchor="end"
          interval={0}
        />
        <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
        <Tooltip contentStyle={{ fontSize: 12 }} />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
        <Bar dataKey="OPEN"   name="Open"   stackId="a" fill="#FAAD9A" radius={[0, 0, 0, 0]} />
        <Bar dataKey="CLOSED" name="Closed" stackId="a" fill="#79ADBD" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
