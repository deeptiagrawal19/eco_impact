"use client"

import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { WaterStressMap } from "@/components/charts/water-stress-map"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { normalizeProviderSlug, providerColor } from "@/lib/chart-palette"
import { useDataCenters, useSustainabilityReports } from "@/lib/dashboard-queries"
import { pickDataCenters, pickModels, pickSustainability } from "@/lib/dashboard-mocks"
import { useImpactEstimate, useModels } from "@/lib/queries"

const GAL_TO_L = 3.785411784

const REGIONS = [
  "",
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

function latestReportPerProvider(
  reports: { provider: string; year: number; total_water_gallons: number | null }[],
) {
  const m = new Map<string, (typeof reports)[0]>()
  for (const r of reports) {
    const cur = m.get(r.provider)
    if (!cur || r.year > cur.year) m.set(r.provider, r)
  }
  return [...m.values()].sort((a, b) => a.provider.localeCompare(b.provider))
}

export default function WaterImpactPage() {
  const {
    data: sustRaw,
    isPending: sP,
    isError: sErr,
  } = useSustainabilityReports()
  const {
    data: dcResRaw,
    isPending: dcP,
    isError: dcErr,
  } = useDataCenters()
  const {
    data: modelsRaw,
    isPending: mP,
    isError: mErr,
  } = useModels()

  const sustReports = React.useMemo(
    () => pickSustainability(sustRaw?.reports, sErr),
    [sustRaw, sErr],
  )
  const dataCenters = React.useMemo(
    () => pickDataCenters(dcResRaw?.data_centers, dcErr),
    [dcResRaw, dcErr],
  )
  const modelsList = React.useMemo(
    () => pickModels(modelsRaw?.models, mErr),
    [modelsRaw, mErr],
  )

  const [queriesPerDay, setQueriesPerDay] = React.useState("10000")
  const [modelId, setModelId] = React.useState("")
  const [region, setRegion] = React.useState<string>("")

  React.useEffect(() => {
    const first = modelsList?.[0]?.id
    if (first && !modelId) setModelId(first)
  }, [modelsList, modelId])

  const qpd = Math.max(0, Number(queriesPerDay) || 0)

  const { data: est, isPending: estP } = useImpactEstimate(
    modelId,
    "text",
    500,
    region || null,
  )

  const waterByProvider = React.useMemo(() => {
    return latestReportPerProvider(sustReports)
      .map((r) => {
        const gal = r.total_water_gallons
        if (gal == null) return null
        return {
          provider: r.provider,
          million_liters: (gal * GAL_TO_L) / 1_000_000,
          fill: providerColor(normalizeProviderSlug(r.provider)),
        }
      })
      .filter((x): x is NonNullable<typeof x> => Boolean(x))
  }, [sustReports])

  const dailyL =
    est?.water.total_ml != null ? (est.water.total_ml * qpd) / 1000 : null
  const monthlyL = dailyL != null ? dailyL * 30 : null
  const annualL = dailyL != null ? dailyL * 365 : null
  const bottlesDay =
    est?.equivalents.water_bottles_500ml != null
      ? est.equivalents.water_bottles_500ml * qpd
      : null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Water impact</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Reported withdrawals, facility stress proxy, and a usage calculator.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Water consumption (latest report, million liters)</CardTitle>
        </CardHeader>
        <CardContent className="h-80">
          {sP && !sustRaw?.reports?.length ? (
            <Skeleton className="h-full w-full" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={waterByProvider} margin={{ bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="provider" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} width={44} />
                <Tooltip
                  formatter={(v) => [`${Number(v ?? 0).toFixed(2)}M L`, "Water"]}
                />
                <Bar dataKey="million_liters" radius={[4, 4, 0, 0]}>
                  {waterByProvider.map((e) => (
                    <Cell key={e.provider} fill={e.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>How much water does your AI usage consume?</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {mP && !modelsRaw?.models?.length ? (
              <Skeleton className="h-48 w-full" />
            ) : (
              <>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="qpd">Queries per day</Label>
                    <Input
                      id="qpd"
                      inputMode="numeric"
                      value={queriesPerDay}
                      onChange={(e) => setQueriesPerDay(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="region">Primary region</Label>
                    <select
                      id="region"
                      className="border-input bg-background h-9 w-full rounded-md border px-2 text-sm"
                      value={region}
                      onChange={(e) => setRegion(e.target.value)}
                    >
                      {REGIONS.map((r) => (
                        <option key={r || "all"} value={r}>
                          {r || "Default / all"}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="model">Primary model</Label>
                  <select
                    id="model"
                    className="border-input bg-background h-9 w-full rounded-md border px-2 text-sm"
                    value={modelId}
                    onChange={(e) => setModelId(e.target.value)}
                  >
                    {modelsList.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.provider})
                      </option>
                    ))}
                  </select>
                </div>
                {estP ? (
                  <Skeleton className="h-36 w-full" />
                ) : (
                  <div className="bg-muted/40 space-y-3 rounded-lg border p-4 text-sm">
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div>
                        <div className="text-muted-foreground text-xs">Daily</div>
                        <div className="font-semibold">
                          {dailyL != null ? `${dailyL.toLocaleString(undefined, { maximumFractionDigits: 0 })} L` : "—"}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground text-xs">Monthly</div>
                        <div className="font-semibold">
                          {monthlyL != null
                            ? `${monthlyL.toLocaleString(undefined, { maximumFractionDigits: 0 })} L`
                            : "—"}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground text-xs">Annual</div>
                        <div className="font-semibold">
                          {annualL != null
                            ? `${annualL.toLocaleString(undefined, { maximumFractionDigits: 0 })} L`
                            : "—"}
                        </div>
                      </div>
                    </div>
                    {bottlesDay != null && (
                      <div>
                        <div className="text-muted-foreground mb-2 text-xs">
                          500&nbsp;ml bottle equivalents / day
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {Array.from({
                            length: Math.min(48, Math.ceil(bottlesDay)),
                          }).map((_, i) => (
                            <span
                              key={i}
                              className="inline-block size-4 rounded-sm bg-sky-500/70"
                              title={`~${bottlesDay.toFixed(0)} bottles`}
                            />
                          ))}
                          {bottlesDay > 48 ? (
                            <span className="text-muted-foreground self-center text-xs">
                              +{Math.round(bottlesDay - 48)} more
                            </span>
                          ) : null}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Water stress vs. data center sites</CardTitle>
            <p className="text-muted-foreground text-xs font-normal">
              Bubble color uses each site&apos;s stress index (0–5); basemap is a
              WRI-style ladder from catalog, not live Aqueduct tiles.
            </p>
          </CardHeader>
          <CardContent>
            {dcP && !dcResRaw?.data_centers?.length ? (
              <Skeleton className="h-[420px] w-full" />
            ) : (
              <WaterStressMap dataCenters={dataCenters} />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
