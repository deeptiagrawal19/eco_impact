"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  BarChart3,
  Droplets,
  Gauge,
  GitCompareArrows,
  LayoutDashboard,
  Map,
  Leaf,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const nav = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/energy", label: "Energy", icon: Gauge },
  { href: "/carbon", label: "Carbon", icon: Leaf },
  { href: "/water", label: "Water", icon: Droplets },
  { href: "/compare-models", label: "Compare Models", icon: GitCompareArrows },
  { href: "/map", label: "Map", icon: Map },
] as const

export function DashboardSidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <div className="flex h-14 items-center gap-2 border-b border-sidebar-border px-4">
        <BarChart3 className="size-6 text-primary" aria-hidden />
        <span className="text-sm font-semibold tracking-tight">
          Eco Impact
        </span>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-3">
        {nav.map(({ href, label, icon: Icon }) => {
          const active =
            pathname === href ||
            (href !== "/" && pathname.startsWith(href))
          return (
            <Button
              key={href}
              variant={active ? "secondary" : "ghost"}
              className={cn(
                "w-full justify-start gap-2",
                active && "border border-primary/30 bg-primary/10 text-primary"
              )}
              asChild
            >
              <Link href={href}>
                <Icon className="size-4 shrink-0" aria-hidden />
                {label}
              </Link>
            </Button>
          )
        })}
      </nav>
    </aside>
  )
}
