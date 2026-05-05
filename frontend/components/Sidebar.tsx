"use client"

import Link from "next/link"
import Image from "next/image"
import { usePathname } from "next/navigation"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Stethoscope, Users, BarChart3, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"
import * as api from "@/lib/api"

const NAV = [
  { href: "/clinician",   label: "Clinician",         icon: Stethoscope },
  { href: "/coordinator", label: "Care Coordinator",  icon: Users },
  { href: "/admin",       label: "Population Health", icon: BarChart3 },
]

export function Sidebar() {
  const pathname = usePathname()
  const qc = useQueryClient()

  const seed = useMutation({
    mutationFn: api.seedDatabase,
    onSuccess: () => { qc.invalidateQueries(); toast.success("Demo data reset") },
    onError: () => toast.error("Failed to reset demo data"),
  })

  return (
    <aside className="flex h-screen w-56 shrink-0 flex-col">

      {/* Logo zone — white, full wordmark */}
      <div className="flex h-[72px] shrink-0 items-center border-b border-r border-[#e9e8e7] bg-white px-5">
        <Link href="/">
          <Image src="/logo.png" alt="FulcrumCare" width={148} height={25} priority />
        </Link>
      </div>

      {/* Nav zone — dark navy */}
      <div className="flex flex-1 flex-col overflow-hidden border-r border-[#121f22] bg-[#010524]">
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-5">
          <p className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-widest text-white/25">
            Demo Roles
          </p>
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname.startsWith(href)
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-[#79ADBD]/20 text-[#9cd5e7]"
                    : "text-white/45 hover:bg-white/5 hover:text-white/75"
                )}
              >
                <Icon className={cn(
                  "h-4 w-4 shrink-0 transition-colors",
                  active ? "text-[#79ADBD]" : "text-white/25"
                )} />
                {label}
              </Link>
            )
          })}
        </nav>

        {/* Bottom utility */}
        <div className="shrink-0 border-t border-white/8 px-3 py-4">
          <button
            onClick={() => seed.mutate()}
            disabled={seed.isPending}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-white/30 transition-colors hover:bg-white/5 hover:text-white/55 disabled:opacity-40"
          >
            <RefreshCw className={cn("h-3.5 w-3.5 shrink-0", seed.isPending && "animate-spin")} />
            {seed.isPending ? "Resetting…" : "Reset Demo Data"}
          </button>
          <p className="mt-3 px-3 text-[10px] text-white/18">
            © 2025 FulcrumCare · Hillhouse CHC
          </p>
        </div>
      </div>

    </aside>
  )
}
