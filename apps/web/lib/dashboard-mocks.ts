/**
 * Offline fallback datasets for the dashboard when API requests fail or return empty data.
 * Model IDs match apps/api/seed.py for consistent /api/impact routes.
 */

import type {
  BestCarbonTimesResponse,
  CarbonByRegion,
  CarbonHistoryPoint,
  DashboardMetrics,
  DataCenter,
  EnergyTimelinePoint,
  EnergyTimelineResponse,
  GPUBenchmark,
  SustainabilityReport,
  TrainingInferenceResponse,
} from "@/lib/dashboard-queries"
import type { ModelCatalogRow } from "@/lib/queries"

const T0 = "2026-03-29T12:00:00.000Z"

function spark(base: number, amp: number): { t: string; value: number }[] {
  return Array.from({ length: 24 }, (_, i) => ({
    t: new Date(Date.UTC(2026, 2, 30, i, 0, 0)).toISOString(),
    value: Math.max(0, base + amp * Math.sin(i / 3.5)),
  }))
}

export const MOCK_DASHBOARD_METRICS: DashboardMetrics = {
  energy_mwh_today: 1428.4,
  energy_trend_pct: -2.4,
  carbon_avg_g_per_kwh: 286,
  carbon_trend_pct: null,
  water_million_liters_today: 2.73,
  water_trend_pct: 1.1,
  queries_billions_today: 3.42,
  queries_trend_pct: 0.8,
  energy_sparkline_24h: spark(48, 6),
  carbon_sparkline_24h: spark(285, 12),
  water_sparkline_24h: spark(110_000, 8000),
  queries_sparkline_24h: spark(140_000_000, 12_000_000),
}

function timelineForHours(nHours: number, utcStart: Date): EnergyTimelinePoint[] {
  const providers = ["openai", "anthropic", "google", "meta"] as const
  const out: EnergyTimelinePoint[] = []
  for (let h = 0; h < nHours; h++) {
    const t = new Date(utcStart)
    t.setUTCHours(t.getUTCHours() + h, 0, 0, 0)
    for (const p of providers) {
      const mwh =
        12 +
        h * 0.02 +
        (p === "openai" ? 38 : p === "google" ? 26 : p === "anthropic" ? 20 : 11) +
        Math.sin(h / 5 + p.length) * 3.5
      out.push({ t: t.toISOString(), provider: p, mwh: Math.round(mwh * 1000) / 1000 })
    }
  }
  return out
}

const MOCK_TIMELINE_START = new Date(Date.UTC(2026, 2, 23, 0, 0, 0))
const MOCK_TIMELINE_24H = timelineForHours(24, MOCK_TIMELINE_START)

export const MOCK_ENERGY_TIMELINE: EnergyTimelineResponse = {
  range: "24h",
  points: MOCK_TIMELINE_24H,
}

export const MOCK_CARBON_BY_REGION: CarbonByRegion = {
  regions: [
    { region: "US-CAL-CISO", carbon_avg: 255, carbon_marginal: 268, time: T0 },
    { region: "US-NY-NYIS", carbon_avg: 305, carbon_marginal: 318, time: T0 },
    { region: "US-MIDA-PJM", carbon_avg: 385, carbon_marginal: 402, time: T0 },
    { region: "DE", carbon_avg: 375, carbon_marginal: 390, time: T0 },
    { region: "GB", carbon_avg: 175, carbon_marginal: 182, time: T0 },
    { region: "FR", carbon_avg: 65, carbon_marginal: 70, time: T0 },
    { region: "IE", carbon_avg: 340, carbon_marginal: 355, time: T0 },
    { region: "SE", carbon_avg: 28, carbon_marginal: 30, time: T0 },
    { region: "NL", carbon_avg: 335, carbon_marginal: 348, time: T0 },
  ],
}

function trainingFromTimeline(
  points: EnergyTimelinePoint[],
): TrainingInferenceResponse {
  const total = points.reduce((s, p) => s + p.mwh, 0)
  const infShare = 0.78
  return {
    training_inference: {
      inference_share: infShare,
      training_share: 1 - infShare,
      inference_mwh: round2(total * infShare),
      training_mwh: round2(total * (1 - infShare)),
    },
    timeline_by_provider: points,
  }
}

function round2(n: number) {
  return Math.round(n * 100) / 100
}

export const MOCK_TRAINING_INFERENCE: TrainingInferenceResponse =
  trainingFromTimeline(MOCK_TIMELINE_24H)

export const MOCK_CARBON_HISTORY: CarbonHistoryPoint[] = (() => {
  const regs = MOCK_CARBON_BY_REGION.regions.map((r) => r.region)
  const pts: CarbonHistoryPoint[] = []
  for (let h = 0; h < 48; h++) {
    const t = new Date(Date.UTC(2026, 2, 29, h, 0, 0)).toISOString()
    for (const region of regs) {
      const base = MOCK_CARBON_BY_REGION.regions.find((x) => x.region === region)?.carbon_avg ?? 300
      pts.push({
        t,
        region,
        carbon_avg: base + (h % 5) * 3,
        carbon_marginal: base * 1.04,
      })
    }
  }
  return pts
})()

export const MOCK_BEST_CARBON_REGIONS = {
  regions: MOCK_CARBON_BY_REGION.regions.map((r, i) => ({
    region: r.region,
    hour_utc_lowest_avg: (3 + i * 2) % 24,
    avg_intensity_g_per_kwh: (r.carbon_avg ?? 300) * 0.88,
  })),
}

export const MOCK_SUSTAINABILITY_REPORTS: SustainabilityReport[] = [
  {
    id: "c0000001-0001-4001-8001-000000000001",
    provider: "google",
    year: 2024,
    total_electricity_gwh: 30800,
    total_water_gallons: 7_200_000_000,
    total_emissions_mtco2e: 12.8e6,
    scope1_mtco2e: 280_000,
    scope2_mtco2e: 4_100_000,
    scope3_mtco2e: 8_420_000,
    renewable_match_percentage: 100,
    avg_pue: 1.1,
    report_url: "https://sustainability.google/reports/2024/",
  },
  {
    id: "c0000001-0001-4001-8001-000000000002",
    provider: "microsoft",
    year: 2024,
    total_electricity_gwh: 24000,
    total_water_gallons: 5_400_000_000,
    total_emissions_mtco2e: 15.2e6,
    scope1_mtco2e: 310_000,
    scope2_mtco2e: 5_900_000,
    scope3_mtco2e: 8_990_000,
    renewable_match_percentage: 100,
    avg_pue: 1.12,
    report_url: "https://www.microsoft.com/sustainability/report",
  },
  {
    id: "c0000001-0001-4001-8001-000000000003",
    provider: "meta",
    year: 2024,
    total_electricity_gwh: 8900,
    total_water_gallons: 2_600_000_000,
    total_emissions_mtco2e: 6.1e6,
    scope1_mtco2e: 95_000,
    scope2_mtco2e: 2_100_000,
    scope3_mtco2e: 3_905_000,
    renewable_match_percentage: 100,
    avg_pue: 1.11,
    report_url: "https://sustainability.fb.com/report/",
  },
]

export const MOCK_DATA_CENTERS: DataCenter[] = [
  {
    id: "b0000001-0001-4001-8001-000000000001",
    provider: "google",
    name: "Google Los Angeles (c/o regional edge)",
    region: "Los Angeles County, CA",
    country: "USA",
    latitude: 34.0522,
    longitude: -118.2437,
    grid_region: "US-CAL-CISO",
    pue: 1.1,
    wue: 1.05,
    capacity_mw: 40,
    renewable_percentage: 92,
    cooling_type: "evaporative + mechanical",
    water_stress_level: 3,
  },
  {
    id: "b0000001-0001-4001-8001-000000000002",
    provider: "microsoft",
    name: "Microsoft East US (Boydton area)",
    region: "Boydton, VA",
    country: "USA",
    latitude: 36.6671,
    longitude: -78.3889,
    grid_region: "US-MIDA-PJM",
    pue: 1.12,
    wue: 0.48,
    capacity_mw: 120,
    renewable_percentage: 88,
    cooling_type: "adiabatic",
    water_stress_level: 2,
  },
  {
    id: "b0000001-0001-4001-8001-000000000003",
    provider: "meta",
    name: "Meta New York (regional footprint)",
    region: "New York, NY",
    country: "USA",
    latitude: 40.7128,
    longitude: -74.006,
    grid_region: "US-NY-NYIS",
    pue: 1.11,
    wue: 0.55,
    capacity_mw: 35,
    renewable_percentage: 100,
    cooling_type: "air-side economizer",
    water_stress_level: 1,
  },
  {
    id: "b0000001-0001-4001-8001-000000000004",
    provider: "google",
    name: "Google Hamina",
    region: "Hamina",
    country: "Finland",
    latitude: 60.5693,
    longitude: 27.1981,
    grid_region: "SE",
    pue: 1.09,
    wue: 0.12,
    capacity_mw: 200,
    renewable_percentage: 97,
    cooling_type: "seawater cooling",
    water_stress_level: 0,
  },
  {
    id: "b0000001-0001-4001-8001-000000000005",
    provider: "amazon",
    name: "AWS eu-west-1 (Dublin)",
    region: "Dublin",
    country: "Ireland",
    latitude: 53.3498,
    longitude: -6.2603,
    grid_region: "IE",
    pue: 1.13,
    wue: 0.22,
    capacity_mw: 180,
    renewable_percentage: 95,
    cooling_type: "indirect evaporative",
    water_stress_level: 2,
  },
]

export const MOCK_GPU_BENCHMARKS: GPUBenchmark[] = [
  {
    id: "gpu-a100",
    gpu_name: "NVIDIA A100 SXM",
    tdp_watts: 400,
    architecture: "Ampere",
    memory_gb: 80,
    memory_bandwidth_tbps: 2,
    inference_tflops: 312,
    training_tflops: 624,
    energy_efficiency_tflops_per_watt: 0.78,
    release_year: 2020,
    source: "NVIDIA datasheet",
  },
  {
    id: "gpu-h100",
    gpu_name: "NVIDIA H100 SXM",
    tdp_watts: 700,
    architecture: "Hopper",
    memory_gb: 80,
    memory_bandwidth_tbps: 3.35,
    inference_tflops: 989,
    training_tflops: 1979,
    energy_efficiency_tflops_per_watt: 1.41,
    release_year: 2022,
    source: "NVIDIA datasheet",
  },
]

export const MOCK_MODEL_CATALOG: ModelCatalogRow[] = [
  {
    id: "a0000001-0001-4001-8001-000000000001",
    name: "GPT-4o",
    provider: "openai",
    model_type: "multimodal",
    energy_per_query_wh: 0.34,
    water_per_query_ml: 0.085,
    co2_per_query_g: 0.1428,
    eco_score: "B",
    parameter_count: null,
    source_paper: null,
  },
  {
    id: "a0000001-0001-4001-8001-000000000002",
    name: "Claude 3.5 Sonnet",
    provider: "anthropic",
    model_type: "multimodal",
    energy_per_query_wh: 0.29,
    water_per_query_ml: 0.0725,
    co2_per_query_g: 0.1218,
    eco_score: "B",
    parameter_count: null,
    source_paper: null,
  },
  {
    id: "a0000001-0001-4001-8001-000000000004",
    name: "Gemini Flash",
    provider: "google",
    model_type: "multimodal",
    energy_per_query_wh: 0.24,
    water_per_query_ml: 0.06,
    co2_per_query_g: 0.1008,
    eco_score: "B",
    parameter_count: null,
    source_paper: null,
  },
  {
    id: "a0000001-0001-4001-8001-000000000005",
    name: "Llama 3.1 8B",
    provider: "meta",
    model_type: "text",
    energy_per_query_wh: 0.032,
    water_per_query_ml: 0.008,
    co2_per_query_g: 0.01344,
    eco_score: "A",
    parameter_count: 8,
    source_paper: null,
  },
]

export function usableDashboardMetrics(d: DashboardMetrics | undefined): boolean {
  return !!d && (d.energy_mwh_today > 1e-6 || d.queries_billions_today > 1e-6)
}

export function pickMetrics(
  d: DashboardMetrics | undefined,
  isError: boolean,
): DashboardMetrics {
  if (!isError && usableDashboardMetrics(d)) return d as DashboardMetrics
  return MOCK_DASHBOARD_METRICS
}

export function pickEnergyTimeline(
  d: EnergyTimelineResponse | undefined,
  isError: boolean,
  range: string,
): EnergyTimelineResponse {
  if (!isError && d && d.points.length > 0) return { ...d, range: d.range || range }
  const r = range.toLowerCase()
  if (r === "7d" || r === "7")
    return { range, points: timelineForHours(168, MOCK_TIMELINE_START) }
  if (r === "30d" || r === "30")
    return { range, points: timelineForHours(720, MOCK_TIMELINE_START) }
  return { ...MOCK_ENERGY_TIMELINE, range }
}

export function pickCarbonByRegion(d: CarbonByRegion | undefined, isError: boolean): CarbonByRegion {
  if (!isError && d && d.regions.some((r) => r.carbon_avg != null)) return d
  return MOCK_CARBON_BY_REGION
}

export function pickTrainingInference(
  d: TrainingInferenceResponse | undefined,
  isError: boolean,
  range = "24h",
): TrainingInferenceResponse {
  if (!isError && d && d.timeline_by_provider.length > 0) return d
  const tl = pickEnergyTimeline(undefined, true, range)
  return trainingFromTimeline(tl.points)
}

export function pickCarbonHistory(
  pts: CarbonHistoryPoint[] | undefined,
  isError: boolean,
): CarbonHistoryPoint[] {
  if (!isError && pts && pts.length > 0) return pts
  return MOCK_CARBON_HISTORY
}

export function pickBestCarbon(r: BestCarbonTimesResponse | undefined, isError: boolean) {
  if (!isError && r && r.regions.some((x) => x.hour_utc_lowest_avg != null)) return r
  return MOCK_BEST_CARBON_REGIONS
}

export function pickSustainability(
  reports: SustainabilityReport[] | undefined,
  isError: boolean,
): SustainabilityReport[] {
  if (!isError && reports && reports.length > 0) return reports
  return MOCK_SUSTAINABILITY_REPORTS
}

export function pickDataCenters(dcs: DataCenter[] | undefined, isError: boolean): DataCenter[] {
  if (!isError && dcs && dcs.length > 0) return dcs
  return MOCK_DATA_CENTERS
}

export function pickGpus(gpus: GPUBenchmark[] | undefined, isError: boolean): GPUBenchmark[] {
  if (!isError && gpus && gpus.length > 0) return gpus
  return MOCK_GPU_BENCHMARKS
}

export function pickModels(models: ModelCatalogRow[] | undefined, isError: boolean): ModelCatalogRow[] {
  if (!isError && models && models.length > 0) return models
  return MOCK_MODEL_CATALOG
}
