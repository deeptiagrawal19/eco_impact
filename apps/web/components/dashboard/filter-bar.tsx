"use client"

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Label } from "@/components/ui/label"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { ChevronDown } from "lucide-react"

import { useDashboardFilters, type EnergyRange } from "./filter-context"

const REGIONS = [
  "US-CAL-CISO",
  "US-NY-NYIS",
  "US-MIDA-PJM",
  "DE",
  "GB",
  "FR",
  "IE",
  "SE",
  "NL",
] as const

const ALL_PROVIDERS = ["openai", "anthropic", "google", "meta", "microsoft", "amazon"]

export function FilterBar() {
  const {
    energyRange,
    setEnergyRange,
    region,
    setRegion,
    providersFilter,
    setProvidersFilter,
  } = useDashboardFilters()

  return (
    <div className="flex flex-wrap items-end gap-4 border-b border-border bg-card/30 px-4 py-3">
      <div className="space-y-1">
        <Label className="text-muted-foreground text-xs">Energy chart range</Label>
        <Tabs
          value={energyRange}
          onValueChange={(v) => setEnergyRange(v as EnergyRange)}
        >
          <TabsList className="h-9">
            <TabsTrigger value="24h" className="px-3 text-xs">
              24h
            </TabsTrigger>
            <TabsTrigger value="7d" className="px-3 text-xs">
              7d
            </TabsTrigger>
            <TabsTrigger value="30d" className="px-3 text-xs">
              30d
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      <div className="space-y-1">
        <Label className="text-muted-foreground text-xs">Region focus</Label>
        <select
          className="border-input bg-background h-9 rounded-md border px-2 text-sm"
          value={region ?? ""}
          onChange={(e) => setRegion(e.target.value || null)}
        >
          <option value="">All</option>
          {REGIONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-1">
        <Label className="text-muted-foreground text-xs">Providers</Label>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="h-9 gap-1">
              {providersFilter.length
                ? `${providersFilter.length} selected`
                : "All providers"}
              <ChevronDown className="size-3 opacity-60" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48">
            {ALL_PROVIDERS.map((p) => (
              <DropdownMenuCheckboxItem
                key={p}
                checked={providersFilter.includes(p)}
                onCheckedChange={(chk) => {
                  setProvidersFilter(
                    chk
                      ? [...providersFilter, p]
                      : providersFilter.filter((x) => x !== p),
                  )
                }}
              >
                {p}
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}
