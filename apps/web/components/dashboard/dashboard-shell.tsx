"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Droplets,
  Gauge,
  GitCompareArrows,
  LayoutDashboard,
  Leaf,
  Map,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"

import { DashboardBreadcrumbs } from "./breadcrumbs"
import { DashboardFilterProvider } from "./filter-context"
import { FilterBar } from "./filter-bar"
import { ThemeToggle } from "./theme-toggle"

const nav = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/energy", label: "Energy", icon: Gauge },
  { href: "/carbon", label: "Carbon", icon: Leaf },
  { href: "/water", label: "Water", icon: Droplets },
  { href: "/compare", label: "Compare Models", icon: GitCompareArrows },
  { href: "/map", label: "Map", icon: Map },
] as const

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = React.useState(false)

  return (
    <DashboardFilterProvider>
      <div className="flex min-h-screen w-full">
        <aside
          className={cn(
            "border-sidebar-border bg-sidebar text-sidebar-foreground sticky top-0 flex h-screen shrink-0 flex-col border-r transition-[width] duration-200",
            collapsed ? "w-[4.5rem]" : "w-56",
          )}
        >
          <div className="flex h-14 items-center justify-between gap-2 border-b border-sidebar-border px-2">
            {!collapsed ? (
              <Link href="/" className="flex items-center gap-2 truncate px-1">
                <BarChart3 aria-hidden className="text-primary size-6 shrink-0" />
                <span className="truncate text-sm font-semibold">Eco Impact</span>
              </Link>
            ) : (
              <BarChart3 className="text-primary mx-auto size-6" aria-hidden />
            )}
          </div>
          <nav className="flex flex-1 flex-col gap-1 p-2">
            {nav.map(({ href, label, icon: Icon }) => {
              const active =
                pathname === href ||
                (href !== "/" && (pathname ?? "").startsWith(href))
              return (
                <Button
                  key={href}
                  variant={active ? "secondary" : "ghost"}
                  size={collapsed ? "icon" : "default"}
                  className={cn(
                    "w-full justify-start gap-2",
                    collapsed && "justify-center px-0",
                    active &&
                      "border-primary/30 bg-primary/10 text-primary border",
                  )}
                  asChild
                >
                  <Link href={href} title={label}>
                    <Icon className="size-4 shrink-0" aria-hidden />
                    {!collapsed ? label : null}
                  </Link>
                </Button>
              )
            })}
          </nav>
          <div className="border-sidebar-border mt-auto border-t p-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="w-full"
              onClick={() => setCollapsed((c) => !c)}
            >
              {collapsed ? (
                <ChevronRight className="size-4" />
              ) : (
                <>
                  <ChevronLeft className="size-4" />
                  <span className="text-xs">Collapse</span>
                </>
              )}
            </Button>
          </div>
        </aside>
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="border-border bg-background/80 sticky top-0 z-10 flex h-14 items-center justify-between gap-4 border-b px-4 backdrop-blur">
            <DashboardBreadcrumbs />
            <div className="flex items-center gap-2">
              <ThemeToggle />
            </div>
          </header>
          <FilterBar />
          <Separator />
          <main className="bg-background min-h-[calc(100vh-7rem)] flex-1 p-4 md:p-6">
            {children}
          </main>
        </div>
      </div>
    </DashboardFilterProvider>
  )
}
