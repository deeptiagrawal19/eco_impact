"use client"

import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { CarbonRegionMap } from "@/components/charts/carbon-region-map"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { providerColor } from "@/lib/chart-palette"
import {
  collectRegionKeysCarbon,
  pivotCarbonHistoryByRegion,
} from "@/lib/chart-utils"
import {
  useBestCarbonTimes,
  useCarbonByRegion,
  useCarbonHistory,
  useSustainabilityReports,
} from "@/lib/dashboard-queries"
import {
  pickBestCarbon,
  pickCarbonByRegion,
  pickCarbonHistory,
  pickSustainability,
} from "@/lib/dashboard-mocks"

const REGION_LINE_PALETTE = [
  "#22d3ee",
  "#a78bfa",
  "#f472b6",
  "#fbbf24",
  "#4ade80",
  "#fb923c",
  "#60a5fa",
  "#f87171",
]

function regionLineColor(i: number): string {
  return REGION_LINE_PALETTE[i % REGION_LINE_PALETTE.length]
}

function latestReportPerProvider(
  reports: {
    provider: string
    year: number
    scope1_mtco2e: number | null
    scope2_mtco2e: number | null
    scope3_mtco2e: number | null
  }[],
) {
  const m = new Map<string, (typeof reports)[0]>()
  for (const r of reports) {
    const cur = m.get(r.provider)
    if (!cur || r.year > cur.year) m.set(r.provider, r)
  }
  return [...m.values()].sort((a, b) => a.provider.localeCompare(b.provider))
}

export default function CarbonAnalysisPage() {
  const [histWindow, setHistWindow] = React.useState<"24h" | "7d" | "30d">("7d")
  const hours = histWindow === "24h" ? 24 : histWindow === "7d" ? 168 : 720

  const {
    data: byRegRaw,
    isPending: regP,
    isError: regErr,
  } = useCarbonByRegion()
  const {
    data: histRaw,
    isPending: histP,
    isError: histErr,
  } = useCarbonHistory(hours)
  const {
    data: bestRaw,
    isPending: bestP,
    isError: bestErr,
  } = useBestCarbonTimes()
  const {
    data: sustRaw,
    isPending: sustP,
    isError: sustErr,
  } = useSustainabilityReports()

  const byReg = React.useMemo(
    () => pickCarbonByRegion(byRegRaw, regErr),
    [byRegRaw, regErr],
  )
  const histPoints = React.useMemo(
    () => pickCarbonHistory(histRaw?.points, histErr),
    [histRaw, histErr],
  )
  const best = React.useMemo(
    () => pickBestCarbon(bestRaw, bestErr),
    [bestRaw, bestErr],
  )
  const sustReports = React.useMemo(
    () => pickSustainability(sustRaw?.reports, sustErr),
    [sustRaw, sustErr],
  )

  const pivoted = React.useMemo(
    () => pivotCarbonHistoryByRegion(histPoints),
    [histPoints],
  )
  const regionKeys = React.useMemo(
    () => collectRegionKeysCarbon(pivoted),
    [pivoted],
  )

  const scopeData = React.useMemo(() => {
    const rows = latestReportPerProvider(sustReports)
    return rows.map((r) => ({
      name: r.provider,
      "Scope 1": r.scope1_mtco2e ?? 0,
      "Scope 2": r.scope2_mtco2e ?? 0,
      "Scope 3": r.scope3_mtco2e ?? 0,
    }))
  }, [sustReports])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Carbon analysis</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Grid intensity by region, historical schedules, and reported emissions scopes.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Carbon intensity (tracked balancing regions)</CardTitle>
        </CardHeader>
        <CardContent>
          {regP && !byRegRaw?.regions?.some((r) => r.carbon_avg != null) ? (
            <Skeleton className="h-[420px] w-full" />
          ) : (
            <CarbonRegionMap data={byReg} />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle>Historical intensity by region</CardTitle>
          <Tabs
            value={histWindow}
            onValueChange={(v) => setHistWindow(v as typeof histWindow)}
          >
            <TabsList className="h-9">
              <TabsTrigger value="24h" className="text-xs">
                24h
              </TabsTrigger>
              <TabsTrigger value="7d" className="text-xs">
                7d
              </TabsTrigger>
              <TabsTrigger value="30d" className="text-xs">
                30d
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent className="h-96">
          {histP && !histRaw?.points?.length ? (
            <Skeleton className="h-full w-full" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={pivoted}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="t" tick={{ fontSize: 9 }} />
                <YAxis
                  tick={{ fontSize: 10 }}
                  width={48}
                  label={{ value: "gCO₂/kWh", angle: -90, position: "insideLeft" }}
                />
                <Tooltip />
                <Legend />
                {regionKeys.map((k, i) => (
                  <Line
                    key={k}
                    type="monotone"
                    dataKey={k}
                    name={k}
                    stroke={regionLineColor(i)}
                    dot={false}
                    strokeWidth={2}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Best time to use AI (lowest avg intensity)</CardTitle>
          </CardHeader>
          <CardContent>
            {bestP && !bestRaw?.regions?.some((r) => r.hour_utc_lowest_avg != null) ? (
              <Skeleton className="h-56 w-full" />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Region</TableHead>
                    <TableHead>Hour (UTC)</TableHead>
                    <TableHead className="text-right">Avg g/kWh</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(best?.regions ?? []).map((r) => (
                    <TableRow key={r.region}>
                      <TableCell className="font-medium">{r.region}</TableCell>
                      <TableCell>
                        {r.hour_utc_lowest_avg != null
                          ? `${String(r.hour_utc_lowest_avg).padStart(2, "0")}:00`
                          : "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        {r.avg_intensity_g_per_kwh != null
                          ? r.avg_intensity_g_per_kwh.toFixed(0)
                          : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Provider emissions (latest sustainability report)</CardTitle>
          </CardHeader>
          <CardContent className="h-80">
            {sustP && !sustRaw?.reports?.length ? (
              <Skeleton className="h-full w-full" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={scopeData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} width={40} />
                  <Tooltip />
                  <Legend />
                  <Bar
                    dataKey="Scope 1"
                    stackId="s"
                    fill={providerColor("meta")}
                    radius={[0, 0, 0, 0]}
                  />
                  <Bar
                    dataKey="Scope 2"
                    stackId="s"
                    fill={providerColor("google")}
                    radius={[0, 0, 0, 0]}
                  />
                  <Bar
                    dataKey="Scope 3"
                    stackId="s"
                    fill={providerColor("anthropic")}
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
            <p className="text-muted-foreground mt-2 text-xs">
              Values are MtCO₂e from uploaded sustainability summaries (Scopes 1–3).
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
