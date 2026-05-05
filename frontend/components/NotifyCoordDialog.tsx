"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import * as api from "@/lib/api"

const schema = z.object({
  coordinator_id: z.coerce.number().min(1, "Select a coordinator"),
  intent: z.string().min(1, "Select an intent"),
  message: z.string().min(5, "Add a message for the coordinator"),
})
type FormData  = z.infer<typeof schema>
type FormInput = z.input<typeof schema>

const INTENTS = [
  "Schedule Appointment",
  "Urgent Follow-up",
  "Insurance Issue",
  "Social Support Needed",
  "Other",
]

interface Props {
  patientId: number
  providerId: number
  patientName: string
}

export function NotifyCoordDialog({ patientId, providerId, patientName }: Props) {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()

  const { data: coordinators = [] } = useQuery({
    queryKey: ["coordinators"],
    queryFn: api.getCoordinators,
  })

  const {
    register, handleSubmit, reset,
    formState: { errors },
  } = useForm<FormInput, any, FormData>({
    resolver: zodResolver(schema),
    defaultValues: { coordinator_id: 0, intent: "", message: "" },
  })

  const submit = useMutation({
    mutationFn: (data: FormData) =>
      api.createTask({
        patient_id: patientId,
        coordinator_id: data.coordinator_id,
        provider_id: providerId,
        intent: data.intent,
        message: data.message,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks", patientId] })
      toast.success("Care coordinator notified")
      reset()
      setOpen(false)
    },
    onError: () => toast.error("Failed to send notification"),
  })

  return (
    <>
      <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
        Notify Coordinator
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Notify Care Coordinator</DialogTitle>
          </DialogHeader>

          <p className="text-xs text-gray-500 -mt-2">Patient: <span className="font-medium text-gray-700">{patientName}</span></p>

          <form onSubmit={handleSubmit((d) => submit.mutate(d))} className="space-y-4">
            {/* Coordinator */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Coordinator</label>
              <select
                {...register("coordinator_id", { valueAsNumber: true })}
                className="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-brand-50"
              >
                <option value={0}>Select coordinator…</option>
                {coordinators.map(c => (
                  <option key={c.coordinator_id} value={c.coordinator_id}>{c.name}</option>
                ))}
              </select>
              {errors.coordinator_id && (
                <p className="text-xs text-red-600 mt-1">{errors.coordinator_id.message}</p>
              )}
            </div>

            {/* Intent */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Intent</label>
              <div className="space-y-1.5">
                {INTENTS.map(intent => (
                  <label key={intent} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="radio"
                      {...register("intent")}
                      value={intent}
                      className="accent-[#4F50FF]"
                    />
                    {intent}
                  </label>
                ))}
              </div>
              {errors.intent && (
                <p className="text-xs text-red-600 mt-1">{errors.intent.message}</p>
              )}
            </div>

            {/* Message */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Message</label>
              <textarea
                {...register("message")}
                rows={3}
                placeholder="Add context for the coordinator…"
                className="w-full rounded-lg border border-gray-200 px-2.5 py-1.5 text-sm resize-none outline-none focus:border-brand focus:ring-2 focus:ring-brand-50"
              />
              {errors.message && (
                <p className="text-xs text-red-600 mt-1">{errors.message.message}</p>
              )}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { reset(); setOpen(false) }}>
                Cancel
              </Button>
              <Button type="submit" disabled={submit.isPending}>
                {submit.isPending ? "Sending…" : "Send"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}
