import type { Metadata } from "next"
import { Instrument_Sans } from "next/font/google"
import "./globals.css"
import { Providers } from "@/app/providers"
import { Sidebar } from "@/components/Sidebar"

const instrumentSans = Instrument_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
})

export const metadata: Metadata = {
  title: "FulcrumCare",
  description: "Preventive dental care coordination for Medicaid patients",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${instrumentSans.variable} h-screen antialiased`}>
      <body className="flex h-full overflow-hidden bg-white">
        <Providers>
          <Sidebar />
          <main className="flex-1 overflow-y-auto">{children}</main>
        </Providers>
      </body>
    </html>
  )
}
