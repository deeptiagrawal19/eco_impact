"use client"

import { useQuery } from "@tanstack/react-query"

/** Dashboard query refetch interval (5 minutes). */
export const DASHBOARD_POLL_MS = 5 * 60 * 1000

async function j<T>(path: string): Promise<T> {
  const r = await fetch(path)
  if (!r.ok) throw new Error(await r.text())
  return r.json() as Promise<T>
}

export type DashboardMetrics = {
  energy_mwh_today: number
  energy_trend_pct: number | null
  carbon_avg_g_per_kwh: number | null
  carbon_trend_pct: number | null
  water_million_liters_today: number
  water_trend_pct: number | null
  queries_billions_today: number
  queries_trend_pct: number | null
  energy_sparkline_24h: { t: string; value: number }[]
  carbon_sparkline_24h: { t: string; value: number }[]
  water_sparkline_24h: { t: string; value: number }[]
  queries_sparkline_24h: { t: string; value: number }[]
}

export function useDashboardMetrics() {
  return useQuery<DashboardMetrics>({
    queryKey: ["dashboard", "metrics"],
    queryFn: () => j<DashboardMetrics>("/api/dashboard/metrics"),
    refetchInterval: DASHBOARD_POLL_MS,
  })
}

export type EnergyTimelinePoint = { t: string; provider: string; mwh: number }
export type EnergyTimelineResponse = { range: string; points: EnergyTimelinePoint[] }

export function useEnergyTimeline(range: "24h" | "7d" | "30d") {
  return useQuery<EnergyTimelineResponse>({
    queryKey: ["dashboard", "energy-timeline", range],
    queryFn: () =>
      j<EnergyTimelineResponse>(`/api/dashboard/energy-timeline?range=${range}`),
    refetchInterval: DASHBOARD_POLL_MS,
  })
}

export type TrainingInferenceResponse = {
  training_inference: {
    inference_share: number
    training_share: number
    inference_mwh: number
    training_mwh: number
  }
  timeline_by_provider: EnergyTimelinePoint[]
}

export function useTrainingInference(range: "24h" | "7d" | "30d" = "24h") {
  return useQuery<TrainingInferenceResponse>({
    queryKey: ["dashboard", "training-inference", range],
    queryFn: () =>
      j<TrainingInferenceResponse>(
        `/api/dashboard/training-inference?range=${range}`,
      ),
    refetchInterval: DASHBOARD_POLL_MS,
  })
}

export type CarbonByRegion = {
  regions: {
    region: string
    carbon_avg: number | null
    carbon_marginal: number | null
    time: string | null
  }[]
}

export function useCarbonByRegion() {
  return useQuery<CarbonByRegion>({
    queryKey: ["dashboard", "carbon-by-region"],
    queryFn: () => j<CarbonByRegion>("/api/dashboard/carbon-by-region"),
    refetchInterval: DASHBOARD_POLL_MS,
  })
}

export type CarbonHistoryPoint = {
  t: string
  region: string
  carbon_avg: number | null
  carbon_marginal: number | null
}

export type CarbonHistoryResponse = { points: CarbonHistoryPoint[] }

export function useCarbonHistory(hours = 168) {
  return useQuery<CarbonHistoryResponse>({
    queryKey: ["dashboard", "carbon-history", hours],
    queryFn: () =>
      j<CarbonHistoryResponse>(`/api/dashboard/carbon-history?hours=${hours}`),
    refetchInterval: DASHBOARD_POLL_MS,
  })
}

export type BestCarbonTimesResponse = {
  regions: {
    region: string
    hour_utc_lowest_avg: number | null
    avg_intensity_g_per_kwh: number | null
  }[]
}

export function useBestCarbonTimes() {
  return useQuery<BestCarbonTimesResponse>({
    queryKey: ["dashboard", "best-carbon-times"],
    queryFn: () => j<BestCarbonTimesResponse>("/api/dashboard/best-carbon-times"),
    refetchInterval: DASHBOARD_POLL_MS,
  })
}

export type DataCenter = {
  id: string
  provider: string
  name: string | null
  region: string
  country: string
  latitude: number | null
  longitude: number | null
  grid_region: string | null
  pue: number | null
  wue: number | null
  capacity_mw: number | null
  renewable_percentage: number | null
  cooling_type: string | null
  water_stress_level: number | null
}

export type DataCentersResponse = { data_centers: DataCenter[] }

export function useDataCenters() {
  return useQuery<DataCentersResponse>({
    queryKey: ["datacenters"],
    queryFn: () => j<DataCentersResponse>("/api/datacenters"),
    refetchInterval: DASHBOARD_POLL_MS,
  })
}

export type SustainabilityReport = {
  id: string
  provider: string
  year: number
  total_electricity_gwh: number | null
  total_water_gallons: number | null
  total_emissions_mtco2e: number | null
  scope1_mtco2e: number | null
  scope2_mtco2e: number | null
  scope3_mtco2e: number | null
  renewable_match_percentage: number | null
  avg_pue: number | null
  report_url: string | null
}

export type SustainabilityReportsResponse = { reports: SustainabilityReport[] }

export function useSustainabilityReports() {
  return useQuery<SustainabilityReportsResponse>({
    queryKey: ["sustainability", "reports"],
    queryFn: () => j<SustainabilityReportsResponse>("/api/sustainability/reports"),
    refetchInterval: DASHBOARD_POLL_MS,
  })
}

export type GPUBenchmark = {
  id: string
  gpu_name: string
  tdp_watts: number | null
  architecture: string | null
  memory_gb: number | null
  memory_bandwidth_tbps: number | null
  inference_tflops: number | null
  training_tflops: number | null
  energy_efficiency_tflops_per_watt: number | null
  release_year: number | null
  source: string | null
}

export type GpuBenchmarksResponse = { gpus: GPUBenchmark[] }

export function useGpuBenchmarks() {
  return useQuery<GpuBenchmarksResponse>({
    queryKey: ["gpu", "benchmarks"],
    queryFn: () => j<GpuBenchmarksResponse>("/api/gpu/benchmarks"),
    refetchInterval: DASHBOARD_POLL_MS,
  })
}

export type CarbonRegionsResponse = {
  regions: { region: string; reading: unknown }[]
}

export function useCarbonRegions() {
  return useQuery({
    queryKey: ["carbon", "regions"],
    queryFn: () =>
      j<{ regions: { region: string; reading: { carbon_intensity_avg: number | null } | null }[] }>(
        "/api/carbon?op=regions",
      ),
    refetchInterval: DASHBOARD_POLL_MS,
  })
}
