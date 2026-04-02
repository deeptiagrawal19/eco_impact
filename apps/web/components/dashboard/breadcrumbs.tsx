"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { ChevronRight } from "lucide-react"

const LABELS: Record<string, string> = {
  "": "Dashboard",
  energy: "Energy",
  carbon: "Carbon",
  water: "Water",
  compare: "Compare Models",
  map: "Map",
}

export function DashboardBreadcrumbs() {
  const pathname = usePathname() || "/"
  const segments = pathname.split("/").filter(Boolean)

  const crumbs: { href: string; label: string }[] = [
    { href: "/", label: "Dashboard" },
  ]

  let acc = ""
  for (const seg of segments) {
    acc += `/${seg}`
    crumbs.push({
      href: acc,
      label: LABELS[seg] ?? seg,
    })
  }

  return (
    <nav className="text-muted-foreground flex flex-wrap items-center gap-1 text-sm">
      {crumbs.map((c, i) => (
        <span key={c.href} className="flex items-center gap-1">
          {i > 0 ? <ChevronRight className="size-3 opacity-50" /> : null}
          {i === crumbs.length - 1 ? (
            <span className="text-foreground font-medium">{c.label}</span>
          ) : (
            <Link href={c.href} className="hover:text-primary transition-colors">
              {c.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  )
}
