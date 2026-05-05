import { cn } from "@/lib/utils"
import type { RiskBucket } from "@/lib/types"

const CONFIG: Record<RiskBucket, { label: string; bg: string; text: string; border: string }> = {
  VERY_HIGH: { label: "Very High", bg: "#fff0eb", text: "#883b14", border: "#f8712e" },
  HIGH:      { label: "High",      bg: "#fde2dd", text: "#bf5521", border: "#FAAD9A" },
  MEDIUM:    { label: "Moderate",  bg: "#e6f3f8", text: "#2d6a7a", border: "#79ADBD" },
  LOW:       { label: "Low",       bg: "#f0f8fb", text: "#42616a", border: "#9cd5e7" },
}

export const RISK_SCORE_COLOR: Record<RiskBucket, string> = {
  VERY_HIGH: "text-[#883b14]",
  HIGH:      "text-[#bf5521]",
  MEDIUM:    "text-[#2d6a7a]",
  LOW:       "text-[#42616a]",
}

interface Props {
  bucket: RiskBucket
  score?: number
  className?: string
}

export function RiskBadge({ bucket, score, className }: Props) {
  const cfg = CONFIG[bucket] ?? CONFIG.LOW
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold",
        className
      )}
      style={{ background: cfg.bg, color: cfg.text, borderColor: cfg.border }}
    >
      {cfg.label}
      {score !== undefined && <span className="opacity-60">· {score.toFixed(0)}</span>}
    </span>
  )
}
