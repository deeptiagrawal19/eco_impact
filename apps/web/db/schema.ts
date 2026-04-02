import {
  bigint,
  doublePrecision,
  integer,
  pgTable,
  primaryKey,
  text,
  timestamp,
  unique,
  uuid,
} from "drizzle-orm/pg-core"

/** Time-series grid carbon (Timescale hypertable on `time`). */
export const carbonIntensityReadings = pgTable(
  "carbon_intensity_readings",
  {
    time: timestamp("time", { withTimezone: true }).notNull(),
    region: text("region").notNull(),
    carbonIntensityAvg: doublePrecision("carbon_intensity_avg"),
    carbonIntensityMarginal: doublePrecision("carbon_intensity_marginal"),
    fossilFuelPercentage: doublePrecision("fossil_fuel_percentage"),
    renewablePercentage: doublePrecision("renewable_percentage"),
    source: text("source").notNull(),
  },
  (t) => [primaryKey({ columns: [t.time, t.region, t.source] })],
)

/** AI model catalog with per-query sustainability estimates. */
export const aiModels = pgTable("ai_models", {
  id: uuid("id").defaultRandom().primaryKey().notNull(),
  name: text("name").notNull(),
  provider: text("provider").notNull(),
  parameterCount: bigint("parameter_count", { mode: "bigint" }),
  modelType: text("model_type"),
  energyPerQueryWh: doublePrecision("energy_per_query_wh"),
  waterPerQueryMl: doublePrecision("water_per_query_ml"),
  co2PerQueryG: doublePrecision("co2_per_query_g"),
  ecoScore: text("eco_score"),
  sourcePaper: text("source_paper"),
  lastUpdated: timestamp("last_updated", { withTimezone: true }),
})

/** Cloud / hyperscaler facility inventory tied to grid regions. */
export const providerDataCenters = pgTable("provider_data_centers", {
  id: uuid("id").defaultRandom().primaryKey().notNull(),
  provider: text("provider").notNull(),
  name: text("name"),
  region: text("region").notNull(),
  country: text("country").notNull(),
  latitude: doublePrecision("latitude"),
  longitude: doublePrecision("longitude"),
  gridRegion: text("grid_region"),
  pue: doublePrecision("pue"),
  wue: doublePrecision("wue"),
  capacityMw: doublePrecision("capacity_mw"),
  renewablePercentage: doublePrecision("renewable_percentage"),
  coolingType: text("cooling_type"),
})

/** Annual sustainability disclosure aggregates. */
export const sustainabilityReports = pgTable(
  "sustainability_reports",
  {
    id: uuid("id").defaultRandom().primaryKey().notNull(),
    provider: text("provider").notNull(),
    year: integer("year").notNull(),
    totalElectricityGwh: doublePrecision("total_electricity_gwh"),
    totalWaterGallons: doublePrecision("total_water_gallons"),
    totalEmissionsMtco2e: doublePrecision("total_emissions_mtco2e"),
    scope1Mtco2e: doublePrecision("scope1_mtco2e"),
    scope2Mtco2e: doublePrecision("scope2_mtco2e"),
    scope3Mtco2e: doublePrecision("scope3_mtco2e"),
    renewableMatchPercentage: doublePrecision("renewable_match_percentage"),
    avgPue: doublePrecision("avg_pue"),
    reportUrl: text("report_url"),
  },
  (t) => [unique("uq_sustainability_provider_year").on(t.provider, t.year)],
)

/** Time-bucketed energy / water / carbon rollups per model (Timescale hypertable). */
export const energyEstimates = pgTable(
  "energy_estimates",
  {
    time: timestamp("time", { withTimezone: true }).notNull(),
    modelId: uuid("model_id")
      .notNull()
      .references(() => aiModels.id, { onDelete: "cascade" }),
    estimatedQueries: bigint("estimated_queries", { mode: "bigint" }),
    totalEnergyMwh: doublePrecision("total_energy_mwh"),
    totalWaterLiters: doublePrecision("total_water_liters"),
    totalCo2Tonnes: doublePrecision("total_co2_tonnes"),
    avgCarbonIntensity: doublePrecision("avg_carbon_intensity"),
    region: text("region"),
  },
  (t) => [primaryKey({ columns: [t.time, t.modelId] })],
)

/** Accelerator reference specs. */
export const gpuBenchmarks = pgTable("gpu_benchmarks", {
  id: uuid("id").defaultRandom().primaryKey().notNull(),
  gpuName: text("gpu_name").notNull(),
  tdpWatts: integer("tdp_watts"),
  architecture: text("architecture"),
  memoryGb: integer("memory_gb"),
  memoryBandwidthTbps: doublePrecision("memory_bandwidth_tbps"),
  inferenceTflops: doublePrecision("inference_tflops"),
  trainingTflops: doublePrecision("training_tflops"),
  energyEfficiencyTflopsPerWatt: doublePrecision("energy_efficiency_tflops_per_watt"),
  releaseYear: integer("release_year"),
  source: text("source"),
})

export const schema = {
  carbonIntensityReadings,
  aiModels,
  providerDataCenters,
  sustainabilityReports,
  energyEstimates,
  gpuBenchmarks,
}

export type CarbonIntensityReadingRow =
  typeof carbonIntensityReadings.$inferSelect
export type AIModelRow = typeof aiModels.$inferSelect
export type ProviderDataCenterRow = typeof providerDataCenters.$inferSelect
export type SustainabilityReportRow = typeof sustainabilityReports.$inferSelect
export type EnergyEstimateRow = typeof energyEstimates.$inferSelect
export type GPUBenchmarkRow = typeof gpuBenchmarks.$inferSelect
