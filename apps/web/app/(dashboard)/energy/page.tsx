"use client"

import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { useDashboardFilters } from "@/components/dashboard/filter-context"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { normalizeProviderSlug, providerColor } from "@/lib/chart-palette"
import { collectProviderKeys, pivotEnergyByProvider } from "@/lib/chart-utils"
import {
  useEnergyTimeline,
  useGpuBenchmarks,
  useTrainingInference,
} from "@/lib/dashboard-queries"
import {
  pickEnergyTimeline,
  pickGpus,
  pickModels,
  pickTrainingInference,
} from "@/lib/dashboard-mocks"
import { useModels } from "@/lib/queries"

const GPU_ORDER = [
  "A100",
  "H100",
  "H200",
  "B200",
  "GB200",
  "MI300X",
]

export default function EnergyPage() {
  const { energyRange, providersFilter } = useDashboardFilters()
  const {
    data: tlRaw,
    isPending: tlP,
    isError: tlErr,
  } = useEnergyTimeline(energyRange)
  const {
    data: tiRaw,
    isPending: tiP,
    isError: tiErr,
  } = useTrainingInference(energyRange)
  const {
    data: gpuRaw,
    isPending: gpuP,
    isError: gpuErr,
  } = useGpuBenchmarks()
  const {
    data: modelsRaw,
    isPending: mP,
    isError: mErr,
  } = useModels()

  const tl = React.useMemo(
    () => pickEnergyTimeline(tlRaw, tlErr, energyRange),
    [tlRaw, tlErr, energyRange],
  )
  const ti = React.useMemo(
    () => pickTrainingInference(tiRaw, tiErr, energyRange),
    [tiRaw, tiErr, energyRange],
  )
  const gpu = React.useMemo(
    () => ({ gpus: pickGpus(gpuRaw?.gpus, gpuErr) }),
    [gpuRaw, gpuErr],
  )
  const models = React.useMemo(
    () => ({ models: pickModels(modelsRaw?.models, mErr) }),
    [modelsRaw, mErr],
  )

  const pivotedLine = React.useMemo(
    () => pivotEnergyByProvider(tl.points ?? [], providersFilter),
    [tl, providersFilter],
  )
  const lineKeys = React.useMemo(
    () => collectProviderKeys(pivotedLine),
    [pivotedLine],
  )
  const lineData = React.useMemo(() => {
    return pivotedLine.map((row) => {
      const o: Record<string, string | number> = { t: row.t }
      let sum = 0
      for (const k of lineKeys) {
        const v = Number((row as Record<string, number>)[k] ?? 0)
        o[k] = v
        sum += v
      }
      o._total = sum
      return o
    })
  }, [pivotedLine, lineKeys])

  const splitBars = React.useMemo(() => {
    const inf = ti.training_inference?.inference_mwh ?? 0
    const tr = ti.training_inference?.training_mwh ?? 0
    return [{ name: "Energy", inference: inf, training: tr }]
  }, [ti])

  const tdpData = React.useMemo(() => {
    const gpus = gpu.gpus ?? []
    return GPU_ORDER.map((needle) => {
      const hit = gpus.find((g) =>
        g.gpu_name.toUpperCase().includes(needle.toUpperCase()),
      )
      return {
        name: needle,
        tdp: hit?.tdp_watts ?? 0,
      }
    }).filter((r) => r.tdp > 0)
  }, [gpu])

  const perQuery = React.useMemo(() => {
    return [...(models.models ?? [])].sort(
      (a, b) =>
        (a.energy_per_query_wh ?? 0) - (b.energy_per_query_wh ?? 0),
    )
  }, [models])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Energy</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Provider timelines, training vs inference split, GPU TDP, and per-query
          baselines.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Consumption by provider (line)</CardTitle>
        </CardHeader>
        <CardContent className="h-80">
          {tlP && !tlRaw?.points?.length ? (
            <Skeleton className="h-full" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={lineData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="t" tick={{ fontSize: 9 }} />
                <YAxis tick={{ fontSize: 10 }} width={44} />
                <Tooltip />
                <Legend />
                {lineKeys.map((k) => (
                  <Line
                    key={k}
                    type="monotone"
                    dataKey={k}
                    stroke={providerColor(k)}
                    dot={false}
                    strokeWidth={2}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Training vs inference (estimated)</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            {tiP && !tiRaw?.timeline_by_provider?.length ? (
              <Skeleton className="h-full" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={splitBars}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar
                    dataKey="inference"
                    stackId="w"
                    fill={providerColor("openai")}
                    name="Inference"
                    radius={[0, 0, 0, 0]}
                  />
                  <Bar
                    dataKey="training"
                    stackId="w"
                    fill={providerColor("anthropic")}
                    name="Training"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle>GPU TDP (reference SKUs)</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            {gpuP && !gpuRaw?.gpus?.length ? (
              <Skeleton className="h-full" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={tdpData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="name" />
                  <YAxis label={{ value: "W", angle: -90, position: "insideLeft" }} />
                  <Tooltip />
                  <Bar dataKey="tdp" fill={providerColor("microsoft")} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Energy per query (catalog)</CardTitle>
        </CardHeader>
        <CardContent className="h-[480px]">
          {mP && !modelsRaw?.models?.length ? (
            <Skeleton className="h-full" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={perQuery.map((m) => ({
                  name: m.name,
                  wh: m.energy_per_query_wh ?? 0,
                  fill: providerColor(normalizeProviderSlug(m.provider)),
                }))}
                margin={{ left: 12, right: 16 }}
              >
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis type="number" />
                <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 10 }} />
                <Tooltip
                  formatter={(v) => [`${Number(v ?? 0).toFixed(3)} Wh`, "Energy"]}
                />
                <Bar dataKey="wh" radius={[0, 4, 4, 0]}>
                  {perQuery.map((m) => (
                    <Cell
                      key={m.id}
                      fill={providerColor(normalizeProviderSlug(m.provider))}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
