"use client"

import { useQuery } from "@tanstack/react-query"

/** Refetch interval for grid-sensitive impact estimates (5 minutes). */
const IMPACT_REFETCH_MS = 5 * 60 * 1000

export type ImpactEquivalents = {
  smartphone_charges: number
  google_searches: number
  driving_km_equivalent: number
  water_bottles_500ml: number
  hours_led_bulb_10w: number
  tree_seconds_offset: number
}

export type ImpactEstimateResponse = {
  energy_wh: number
  carbon: {
    avg_g: number | null
    marginal_g: number | null
    intensity_avg_g_per_kwh: number | null
    intensity_marginal_g_per_kwh: number | null
    grid_region_used: string | null
  }
  water: {
    direct_ml: number | null
    indirect_ml: number | null
    total_ml: number | null
    wue_l_per_kwh: number | null
  }
  equivalents: ImpactEquivalents
  methodology_note: string
}

export type ModelComparisonRow = {
  model_id: string
  model_name: string
  provider: string
  energy_wh: number
  carbon_g_avg: number | null
  carbon_g_marginal: number | null
  water_direct_ml: number | null
  water_indirect_ml: number | null
  water_total_ml: number | null
  eco_score: string | null
  percentage_vs_best: number
}

export type ImpactCompareResponse = {
  task_type: string
  region: string | null
  models: ModelComparisonRow[]
}

export type ModelCatalogRow = {
  id: string
  name: string
  provider: string
  model_type: string | null
  energy_per_query_wh: number | null
  water_per_query_ml: number | null
  co2_per_query_g: number | null
  eco_score: string | null
  parameter_count: number | null
  source_paper: string | null
}

export type ImpactModelsResponse = {
  models: ModelCatalogRow[]
}

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || res.statusText)
  }
  return res.json() as Promise<T>
}

/** Single-model impact estimate (energy, carbon, water); refetches on IMPACT_REFETCH_MS. */
export function useImpactEstimate(
  model: string,
  queryType: string,
  tokenCount: number,
  region?: string | null,
  imageCount?: number | null,
) {
  return useQuery({
    queryKey: [
      "impact",
      "estimate",
      model,
      queryType,
      tokenCount,
      region ?? "",
      imageCount ?? "",
    ],
    queryFn: async () => {
      const res = await fetch("/api/impact/estimate", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          model,
          query_type: queryType,
          token_count: tokenCount,
          region: region || undefined,
          image_count: imageCount ?? undefined,
        }),
      })
      return parseJson<ImpactEstimateResponse>(res)
    },
    enabled: Boolean(model),
    refetchInterval: IMPACT_REFETCH_MS,
  })
}

/** Ranked models for a task type and optional region. */
export function useModelComparison(
  taskType: string,
  region?: string | null,
  tokenCount = 500,
) {
  return useQuery({
    queryKey: ["impact", "compare", taskType, region ?? "", tokenCount],
    queryFn: async () => {
      const params = new URLSearchParams({
        task_type: taskType,
        token_count: String(tokenCount),
      })
      if (region) params.set("region", region)
      const res = await fetch(`/api/impact/compare?${params.toString()}`, {
        headers: { Accept: "application/json" },
      })
      return parseJson<ImpactCompareResponse>(res)
    },
    refetchInterval: IMPACT_REFETCH_MS,
  })
}

/** Full ``ai_models`` catalog (baselines). */
export function useModels() {
  return useQuery<ImpactModelsResponse>({
    queryKey: ["impact", "models"],
    queryFn: async () => {
      const res = await fetch("/api/impact/models", {
        headers: { Accept: "application/json" },
      })
      return parseJson<ImpactModelsResponse>(res)
    },
    refetchInterval: IMPACT_REFETCH_MS,
  })
}
