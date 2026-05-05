"use client"

import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import * as api from "@/lib/api"
import type { CareGap } from "@/lib/types"

const schema = z.object({
  method:      z.string().min(1, "Select a method"),
  outcome:     z.string().min(1, "Select an outcome"),
  notes:       z.string().optional(),
  care_gap_id: z.coerce.number().optional(),
})
type FormData  = z.infer<typeof schema>
type FormInput = z.input<typeof schema>

const METHODS  = ["Phone Call", "Text Message", "Email", "In-Person"]
const OUTCOMES = ["Reached", "Left Voicemail", "No Answer", "Appointment Scheduled", "Declined"]

interface Props {
  patientId:     number
  coordinatorId: number
  openGaps?:     CareGap[]
  onSuccess?:    () => void
}

export function LogOutreachForm({ patientId, coordinatorId, openGaps = [], onSuccess }: Props) {
  const qc = useQueryClient()

  const {
    register, handleSubmit, reset,
    formState: { errors },
  } = useForm<FormInput, any, FormData>({
    resolver: zodResolver(schema),
    defaultValues: { method: "", outcome: "", notes: "", care_gap_id: undefined },
  })

  const submit = useMutation({
    mutationFn: (data: FormData) =>
      api.logOutreach({
        patient_id:    patientId,
        coordinator_id: coordinatorId,
        method:        data.method,
        outcome:       data.outcome,
        notes:         data.notes || null,
        care_gap_id:   data.care_gap_id || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["outreach",  patientId] })
      qc.invalidateQueries({ queryKey: ["patient",   patientId] })
      qc.invalidateQueries({ queryKey: ["coord-patients", coordinatorId] })
      toast.success("Outreach logged")
      reset()
      onSuccess?.()
    },
    onError: () => toast.error("Failed to log outreach"),
  })

  const fieldCls = "w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-brand-50"

  return (
    <form onSubmit={handleSubmit((d) => submit.mutate(d))} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        {/* Method */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Method</label>
          <select {...register("method")} className={fieldCls}>
            <option value="">Select…</option>
            {METHODS.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          {errors.method && <p className="text-xs text-red-600 mt-1">{errors.method.message}</p>}
        </div>

        {/* Outcome */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Outcome</label>
          <select {...register("outcome")} className={fieldCls}>
            <option value="">Select…</option>
            {OUTCOMES.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
          {errors.outcome && <p className="text-xs text-red-600 mt-1">{errors.outcome.message}</p>}
        </div>
      </div>

      {/* Link to care gap */}
      {openGaps.length > 0 && (
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Link to Care Gap <span className="font-normal text-gray-400">(optional)</span>
          </label>
          <select {...register("care_gap_id")} className={fieldCls}>
            <option value="">None</option>
            {openGaps.map(g => (
              <option key={g.gap_id} value={g.gap_id}>{g.name}</option>
            ))}
          </select>
        </div>
      )}

      {/* Notes */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Notes <span className="font-normal text-gray-400">(optional)</span>
        </label>
        <textarea
          {...register("notes")}
          rows={2}
          placeholder="Any additional context…"
          className={`${fieldCls} resize-none`}
        />
      </div>

      <Button type="submit" size="sm" disabled={submit.isPending} className="w-full">
        {submit.isPending ? "Logging…" : "Log Outreach"}
      </Button>
    </form>
  )
}
