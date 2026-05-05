"use client"

import Link from "next/link"
import Image from "next/image"
import { usePathname } from "next/navigation"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import * as api from "@/lib/api"
import { Button } from "@/components/ui/button"

const NAV_LINKS = [
  { href: "/clinician",   label: "Clinician" },
  { href: "/coordinator", label: "Care Coordinator" },
  { href: "/admin",       label: "Population Health" },
]

export function Navbar() {
  const pathname = usePathname()
  const qc = useQueryClient()

  const seed = useMutation({
    mutationFn: api.seedDatabase,
    onSuccess: () => {
      qc.invalidateQueries()
      toast.success("Demo data reset successfully")
    },
    onError: () => toast.error("Failed to reset demo data"),
  })

  return (
    <header className="sticky top-0 z-40 border-b bg-white/90 backdrop-blur supports-backdrop-filter:bg-white/80">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
        {/* Brand */}
        <Link href="/" className="flex items-center">
          <Image
            src="/logo.png"
            alt="FulcrumCare"
            height={28}
            width={197}
            priority
          />
        </Link>

        {/* Nav links */}
        <nav className="flex items-center gap-1">
          {NAV_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                pathname.startsWith(href)
                  ? "bg-brand-50 text-brand"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              )}
            >
              {label}
            </Link>
          ))}
        </nav>

        {/* Reset demo */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => seed.mutate()}
          disabled={seed.isPending}
          className="text-xs"
        >
          {seed.isPending ? "Resetting…" : "Reset Demo Data"}
        </Button>
      </div>
    </header>
  )
}
