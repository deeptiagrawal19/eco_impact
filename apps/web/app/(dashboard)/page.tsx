"use client"

import * as React from "react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { ModelEfficiencyTable } from "@/components/dashboard/model-efficiency-table"
import { MetricCard } from "@/components/dashboard/metric-card"
import { useDashboardFilters } from "@/components/dashboard/filter-context"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { carbonIntensityColor, providerColor } from "@/lib/chart-palette"
import { collectProviderKeys, pivotEnergyByProvider } from "@/lib/chart-utils"
import {
  useCarbonByRegion,
  useDashboardMetrics,
  useEnergyTimeline,
} from "@/lib/dashboard-queries"
import {
  pickCarbonByRegion,
  pickEnergyTimeline,
  pickMetrics,
} from "@/lib/dashboard-mocks"

export default function DashboardHomePage() {
  const {
    data: metricsRaw,
    isPending: mPending,
    isError: mErr,
  } = useDashboardMetrics()
  const { energyRange, providersFilter } = useDashboardFilters()
  const {
    data: tlRaw,
    isPending: tlPending,
    isError: tlErr,
  } = useEnergyTimeline(energyRange)
  const {
    data: carbRegRaw,
    isPending: cPending,
    isError: cErr,
  } = useCarbonByRegion()

  const metrics = React.useMemo(
    () => pickMetrics(metricsRaw, mErr),
    [metricsRaw, mErr],
  )
  const tl = React.useMemo(
    () => pickEnergyTimeline(tlRaw, tlErr, energyRange),
    [tlRaw, tlErr, energyRange],
  )
  const carbReg = React.useMemo(
    () => pickCarbonByRegion(carbRegRaw, cErr),
    [carbRegRaw, cErr],
  )

  const pivoted = React.useMemo(
    () => pivotEnergyByProvider(tl.points ?? [], providersFilter),
    [tl, providersFilter],
  )
  const provKeys = React.useMemo(() => collectProviderKeys(pivoted), [pivoted])

  const carbonRows = carbReg.regions ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          AI workload estimates, grid carbon intensity, and model efficiency.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {mPending && !metricsRaw ? (
          [...Array(4)].map((_, i) => <Skeleton key={i} className="h-36 rounded-xl" />)
        ) : (
          <>
            <MetricCard
              title="AI energy today"
              valueLabel={`${(metrics.energy_mwh_today ?? 0).toFixed(2)} MWh`}
              trendPct={metrics.energy_trend_pct}
              sparkline={metrics.energy_sparkline_24h ?? []}
            />
            <MetricCard
              title="Avg grid carbon (MVP regions)"
              valueLabel={`${metrics.carbon_avg_g_per_kwh != null ? metrics.carbon_avg_g_per_kwh.toFixed(0) : "—"} g/kWh`}
              trendPct={metrics.carbon_trend_pct}
              sparkline={metrics.carbon_sparkline_24h ?? []}
              valueStyle={
                metrics.carbon_avg_g_per_kwh != null
                  ? { color: carbonIntensityColor(metrics.carbon_avg_g_per_kwh) }
                  : undefined
              }
            />
            <MetricCard
              title="Water (AI workloads) today"
              valueLabel={`${(metrics.water_million_liters_today ?? 0).toFixed(2)}M L`}
              trendPct={metrics.water_trend_pct}
              sparkline={metrics.water_sparkline_24h ?? []}
            />
            <MetricCard
              title="Queries (estimated) today"
              valueLabel={`${(metrics.queries_billions_today ?? 0).toFixed(3)}B`}
              trendPct={metrics.queries_trend_pct}
              sparkline={metrics.queries_sparkline_24h ?? []}
            />
          </>
        )}
      </div>

      <Card className="border-border/80">
        <CardHeader className="pb-2">
          <CardTitle>Energy by provider</CardTitle>
          <p className="text-muted-foreground text-xs">
            Stacked facility MWh — toggle range in filter bar.
          </p>
        </CardHeader>
        <CardContent className="h-80 pt-0">
          {tlPending && !tlRaw?.points?.length ? (
            <Skeleton className="h-full w-full" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={pivoted}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="t"
                  tick={{ fontSize: 10 }}
                  tickFormatter={(v) =>
                    String(v).slice(5, 16).replace("T", " ")
                  }
                />
                <YAxis tick={{ fontSize: 10 }} width={40} />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--popover))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                  }}
                />
                {provKeys.map((pk) => (
                  <Area
                    key={pk}
                    type="monotone"
                    dataKey={pk}
                    name={pk}
                    stackId="1"
                    stroke={providerColor(pk)}
                    fill={providerColor(pk)}
                    fillOpacity={0.6}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/80">
          <CardHeader className="pb-2">
            <CardTitle>Carbon intensity by region</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            {cPending && !carbRegRaw?.regions?.some((r) => r.carbon_avg != null) ? (
              <Skeleton className="h-full w-full" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={carbonRows.map((r) => ({
                    name: r.region,
                    v: r.carbon_avg ?? 0,
                  }))}
                  margin={{ left: 8, right: 24 }}
                >
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={100}
                    tick={{ fontSize: 10 }}
                  />
                  <Tooltip
                    formatter={(v, _n, p) => [
                      `${Number(v ?? 0).toFixed(0)} g/kWh`,
                      String((p as { payload?: { name?: string } }).payload?.name),
                    ]}
                  />
                  <Bar dataKey="v" radius={[0, 4, 4, 0]}>
                    {carbonRows.map((r) => (
                      <Cell
                        key={r.region}
                        fill={
                          r.carbon_avg != null
                            ? carbonIntensityColor(r.carbon_avg)
                            : "#475569"
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/80">
          <CardHeader className="pb-2">
            <CardTitle>Model efficiency ranking</CardTitle>
            <p className="text-muted-foreground text-xs">
              Model catalog (sortable).
            </p>
          </CardHeader>
          <CardContent className="max-h-[420px] overflow-auto">
            <ModelEfficiencyTable />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
