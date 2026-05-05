import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface Props {
  label: string
  value: string | number
  sub?: string
  className?: string
  valueClassName?: string
}

export function StatCard({ label, value, sub, className, valueClassName }: Props) {
  return (
    <Card className={cn("rounded-xl border border-gray-200 shadow-none hover:shadow-sm transition-shadow", className)}>
      <CardContent className="p-4">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
        <p className={cn("mt-1 text-2xl font-bold text-gray-900", valueClassName)}>{value}</p>
        {sub && <p className="mt-0.5 text-xs text-gray-400">{sub}</p>}
      </CardContent>
    </Card>
  )
}
