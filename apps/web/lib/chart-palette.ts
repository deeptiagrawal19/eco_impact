/** Consistent provider colors for charts (dashboard spec). */

export const PROVIDER_COLORS: Record<string, string> = {
  openai: "#10b981",
  anthropic: "#8b5cf6",
  google: "#3b82f6",
  meta: "#f97316",
  microsoft: "#06b6d4",
  midjourney: "#ec4899",
  amazon: "#f59e0b",
  default: "#94a3b8",
}

export function providerColor(provider: string): string {
  const k = provider.toLowerCase().trim()
  return PROVIDER_COLORS[k] ?? PROVIDER_COLORS.default
}

/** Map display names from sustainability reports to chart slug keys. */
export function normalizeProviderSlug(name: string): string {
  const n = name.trim().toLowerCase()
  if (n.includes("openai")) return "openai"
  if (n.includes("anthropic")) return "anthropic"
  if (n.includes("google")) return "google"
  if (n.includes("meta")) return "meta"
  if (n.includes("microsoft")) return "microsoft"
  if (n.includes("amazon") || n.includes("aws")) return "amazon"
  return n.replace(/[^a-z0-9]/g, "") || "default"
}

/** Carbon intensity gradient: low (green) → high (red), 200–550 g/kWh typical window. */
export function carbonIntensityColor(gPerKwh: number, min = 200, max = 550): string {
  const t = Math.min(1, Math.max(0, (gPerKwh - min) / (max - min)))
  const r = Math.round(t * 220 + (1 - t) * 16)
  const g = Math.round((1 - t) * 185 + t * 40)
  const b = Math.round((1 - t) * 129 + t * 40)
  return `rgb(${r},${g},${b})`
}
