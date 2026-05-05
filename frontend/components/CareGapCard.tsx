"use client"

import { cn } from "@/lib/utils"
import type { CareGap } from "@/lib/types"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import * as api from "@/lib/api"
import { Button } from "@/components/ui/button"

interface Props {
  gap: CareGap
  patientId: number
  closedBy?: string
}

const STATUS_STYLE: Record<string, string> = {
  OPEN:           "bg-red-50 border-red-200 text-red-700",
  CLOSED:         "bg-green-50 border-green-200 text-green-700",
  NOT_APPLICABLE: "bg-gray-50 border-gray-200 text-gray-500",
}

export function CareGapCard({ gap, patientId, closedBy = "Clinician" }: Props) {
  const qc = useQueryClient()

  const close = useMutation({
    mutationFn: () => api.closeGap(gap.gap_id, { closed_by: closedBy }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["gaps", patientId] })
      qc.invalidateQueries({ queryKey: ["patient", patientId] })
      toast.success("Care gap closed")
    },
    onError: () => toast.error("Failed to close gap"),
  })

  return (
    <div className="rounded-lg border border-gray-200 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900">{gap.name}</p>
          <p className="text-xs text-gray-500 mt-0.5">{gap.description}</p>
        </div>
        <span className={cn(
          "shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full border",
          STATUS_STYLE[gap.gap_status] ?? STATUS_STYLE.NOT_APPLICABLE
        )}>
          {gap.gap_status === "NOT_APPLICABLE" ? "N/A" : gap.gap_status}
        </span>
      </div>

      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-gray-400">
          {gap.category} · weight {gap.priority_weight.toFixed(1)}
        </span>
        {gap.gap_status === "OPEN" && (
          <Button
            size="xs"
            variant="outline"
            onClick={() => close.mutate()}
            disabled={close.isPending}
          >
            {close.isPending ? "Closing…" : "Close Gap"}
          </Button>
        )}
        {gap.gap_status === "CLOSED" && gap.closed_at && (
          <span className="text-xs text-gray-400">
            Closed {new Date(gap.closed_at).toLocaleDateString()}
            {gap.closed_by && ` · ${gap.closed_by}`}
          </span>
        )}
      </div>
    </div>
  )
}
