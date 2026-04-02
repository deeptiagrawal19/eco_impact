import type {
  CarbonHistoryPoint,
  EnergyTimelinePoint,
} from "@/lib/dashboard-queries"

export function pivotEnergyByProvider(
  points: EnergyTimelinePoint[],
  providersFilter: string[],
): Record<string, string | number>[] {
  const map = new Map<string, Record<string, number>>()
  for (const p of points) {
    const prov = p.provider.toLowerCase()
    if (providersFilter.length && !providersFilter.includes(prov)) continue
    const tKey = p.t
    if (!map.has(tKey)) map.set(tKey, {})
    const row = map.get(tKey)!
    row[prov] = (row[prov] ?? 0) + p.mwh
  }
  return [...map.entries()]
    .sort(([a], [b]) => String(a).localeCompare(String(b)))
    .map(([t, rest]) => ({ t: String(t), ...rest }))
}

export function collectProviderKeys(
  rows: Record<string, string | number>[],
): string[] {
  const s = new Set<string>()
  for (const r of rows) {
    for (const k of Object.keys(r)) {
      if (k !== "t") s.add(k)
    }
  }
  return [...s].sort()
}

/** Pivot carbon history into tall rows `{ t, [region]: g/kWh }` for multi-series lines. */
export function pivotCarbonHistoryByRegion(
  points: CarbonHistoryPoint[],
): Record<string, string | number | null>[] {
  const map = new Map<string, Record<string, string | number | null>>()
  for (const p of points) {
    if (!map.has(p.t))
      map.set(p.t, { t: String(p.t) } as Record<string, string | number | null>)
    const row = map.get(p.t)!
    row[p.region] = p.carbon_avg
  }
  return [...map.entries()]
    .sort(([a], [b]) => String(a).localeCompare(String(b)))
    .map(([, row]) => row)
}

export function collectRegionKeysCarbon(
  rows: Record<string, string | number | null>[],
): string[] {
  const s = new Set<string>()
  for (const r of rows) {
    for (const k of Object.keys(r)) {
      if (k !== "t") s.add(k)
    }
  }
  return [...s].sort()
}
