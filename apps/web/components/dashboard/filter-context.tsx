"use client"

import * as React from "react"

export type EnergyRange = "24h" | "7d" | "30d"

type DashboardFilterState = {
  energyRange: EnergyRange
  setEnergyRange: (v: EnergyRange) => void
  region: string | null
  setRegion: (v: string | null) => void
  providersFilter: string[]
  setProvidersFilter: (v: string[]) => void
}

const Ctx = React.createContext<DashboardFilterState | null>(null)

export function DashboardFilterProvider({
  children,
}: {
  children: React.ReactNode
}) {
  const [energyRange, setEnergyRange] = React.useState<EnergyRange>("24h")
  const [region, setRegion] = React.useState<string | null>(null)
  const [providersFilter, setProvidersFilter] = React.useState<string[]>([])

  const value = React.useMemo(
    () => ({
      energyRange,
      setEnergyRange,
      region,
      setRegion,
      providersFilter,
      setProvidersFilter,
    }),
    [energyRange, region, providersFilter],
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useDashboardFilters() {
  const v = React.useContext(Ctx)
  if (!v) throw new Error("useDashboardFilters outside provider")
  return v
}
