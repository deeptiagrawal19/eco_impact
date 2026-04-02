/** Shared API contract types for the eco-impact dashboard. */

export interface HealthResponse {
  status: "ok";
}

export interface EnergyReading {
  id: string;
  region: string;
  timestamp: string;
  kwh: number;
}

export interface CarbonIntensityPoint {
  timestamp: string;
  gco2PerKwh: number;
}

export interface WaterUsageRecord {
  id: string;
  facilityId: string;
  liters: number;
  date: string;
}
