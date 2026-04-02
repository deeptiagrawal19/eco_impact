"use client"

import * as React from "react"
import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts"

import { useDashboardFilters } from "@/components/dashboard/filter-context"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ecoBadgeClass } from "@/lib/eco-badge"
import { normalizeProviderSlug, providerColor } from "@/lib/chart-palette"
import { pickModels } from "@/lib/dashboard-mocks"
import type { ModelCatalogRow } from "@/lib/queries"
import { useImpactEstimate, useModels } from "@/lib/queries"

function ecoLetterScore(letter: string | null | undefined): number {
  const m: Record<string, number> = {
    A: 100,
    B: 86,
    C: 72,
    D: 58,
    F: 42,
  }
  const k = (letter ?? "C").toUpperCase()
  return m[k] ?? 65
}

function spanScore(
  val: number | null | undefined,
  vals: (number | null | undefined)[],
  lowerIsBetter: boolean,
): number {
  const nums = vals
    .map((v) => Number(v ?? NaN))
    .filter((n) => Number.isFinite(n) && n >= 0)
  if (!nums.length) return 55
  const min = Math.min(...nums)
  const max = Math.max(...nums)
  const v = Number(val ?? NaN)
  if (!Number.isFinite(v)) return 40
  if (max <= min) return 100
  if (lowerIsBetter) return (100 * (max - v)) / (max - min)
  return (100 * (v - min)) / (max - min)
}

function performanceScore(m: ModelCatalogRow, models: ModelCatalogRow[]): number {
  const params = models.map((x) => x.parameter_count)
  const base = spanScore(m.parameter_count, params, false)
  const grade = ecoLetterScore(m.eco_score)
  return Math.round(0.55 * base + 0.45 * grade)
}

function buildRadarRows(models: ModelCatalogRow[]) {
  const e = models.map((m) => m.energy_per_query_wh)
  const c = models.map((m) => m.co2_per_query_g)
  const w = models.map((m) => m.water_per_query_ml)
  const rows: Record<string, string | number>[] = [
    { subject: "Energy" },
    { subject: "Carbon" },
    { subject: "Water" },
    { subject: "Performance" },
  ]
  for (const m of models) {
    const key = m.id
    rows[0][key] = Math.round(spanScore(m.energy_per_query_wh, e, true))
    rows[1][key] = Math.round(spanScore(m.co2_per_query_g, c, true))
    rows[2][key] = Math.round(spanScore(m.water_per_query_ml, w, true))
    rows[3][key] = performanceScore(m, models)
  }
  return rows
}

export default function CompareModelsPage() {
  const { region } = useDashboardFilters()
  const { data, isPending, isError } = useModels()
  const all = React.useMemo(
    () => pickModels(data?.models, isError),
    [data?.models, isError],
  )

  const [picked, setPicked] = React.useState<string[]>([])
  const seeded = React.useRef(false)

  React.useEffect(() => {
    if (!all.length || seeded.current) return
    seeded.current = true
    setPicked(all.slice(0, Math.min(3, all.length)).map((m) => m.id))
  }, [all])

  const toggle = (id: string) => {
    setPicked((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id)
      if (prev.length >= 4) return [...prev.slice(1), id]
      return [...prev, id]
    })
  }

  const selected = React.useMemo(() => {
    return picked
      .map((id) => all.find((m) => m.id === id))
      .filter((m): m is ModelCatalogRow => Boolean(m))
  }, [picked, all])

  const radarData = React.useMemo(
    () => (selected.length >= 2 ? buildRadarRows(selected) : []),
    [selected],
  )

  const [fromId, setFromId] = React.useState("")
  const [toId, setToId] = React.useState("")
  const [monthlyQueries, setMonthlyQueries] = React.useState("100000")

  React.useEffect(() => {
    if (all.length < 2) return
    if (!fromId) setFromId(all[0].id)
    if (!toId) setToId(all[1].id)
  }, [all, fromId, toId])

  const mq = Math.max(0, Number(monthlyQueries) || 0)
  const fromEst = useImpactEstimate(fromId, "text", 500, region)
  const toEst = useImpactEstimate(toId, "text", 500, region)

  const saveKwh =
    fromEst.data && toEst.data
      ? ((fromEst.data.energy_wh - toEst.data.energy_wh) * mq) / 1000
      : null
  const saveL =
    fromEst.data?.water.total_ml != null && toEst.data?.water.total_ml != null
      ? ((fromEst.data.water.total_ml - toEst.data.water.total_ml) * mq) / 1000
      : null
  const saveKgCo2 =
    fromEst.data?.carbon.avg_g != null && toEst.data?.carbon.avg_g != null
      ? ((fromEst.data.carbon.avg_g - toEst.data.carbon.avg_g) * mq) / 1000
      : null

  const fromName = all.find((m) => m.id === fromId)?.name ?? fromId
  const toName = all.find((m) => m.id === toId)?.name ?? toId

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Model comparison</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Compare up to four models: radar chart, metrics table, and savings estimate.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Select models (max 4)</CardTitle>
        </CardHeader>
        <CardContent>
          {isPending && !data?.models?.length ? (
            <Skeleton className="h-40 w-full" />
          ) : (
            <div className="max-h-56 space-y-2 overflow-y-auto pr-1 text-sm">
              {all.map((m) => (
                <label
                  key={m.id}
                  className="hover:bg-muted/50 flex cursor-pointer items-center gap-2 rounded-md border px-2 py-1.5"
                >
                  <input
                    type="checkbox"
                    checked={picked.includes(m.id)}
                    onChange={() => toggle(m.id)}
                    className="accent-primary"
                  />
                  <span className="flex-1 truncate">{m.name}</span>
                  <span className="text-muted-foreground text-xs">{m.provider}</span>
                </label>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Impact profile (higher is better on all axes)</CardTitle>
          </CardHeader>
          <CardContent className="h-96">
            {selected.length < 2 ? (
              <p className="text-muted-foreground text-sm">
                Choose at least two models to render the radar.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} outerRadius="78%">
                  <PolarGrid className="stroke-muted" />
                  <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} />
                  <Tooltip />
                  <Legend />
                  {selected.map((m) => (
                    <Radar
                      key={m.id}
                      name={m.name}
                      dataKey={m.id}
                      stroke={providerColor(normalizeProviderSlug(m.provider))}
                      fill={providerColor(normalizeProviderSlug(m.provider))}
                      fillOpacity={0.12}
                    />
                  ))}
                </RadarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Switch and save</CardTitle>
            <p className="text-muted-foreground text-xs font-normal">
              Uses /api/impact/estimate (500 tokens per query) and the header region filter.
              Savings scale linearly with monthly query count.
            </p>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="space-y-2">
              <Label htmlFor="mq">Monthly queries</Label>
              <Input
                id="mq"
                inputMode="numeric"
                value={monthlyQueries}
                onChange={(e) => setMonthlyQueries(e.target.value)}
              />
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="space-y-1">
                <Label>From</Label>
                <select
                  className="border-input bg-background h-9 w-full rounded-md border px-2 text-sm"
                  value={fromId}
                  onChange={(e) => setFromId(e.target.value)}
                >
                  {all.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <Label>To</Label>
                <select
                  className="border-input bg-background h-9 w-full rounded-md border px-2 text-sm"
                  value={toId}
                  onChange={(e) => setToId(e.target.value)}
                >
                  {all.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            {fromEst.isPending || toEst.isPending ? (
              <Skeleton className="h-24 w-full" />
            ) : saveKwh != null && saveL != null && saveKgCo2 != null ? (
              <div className="bg-muted/40 rounded-lg border p-3 leading-relaxed">
                <strong>{fromName}</strong> → <strong>{toName}</strong> at this query volume: about{" "}
                <strong>{saveKwh.toFixed(1)} kWh</strong> / month,{" "}
                <strong>{saveL.toLocaleString(undefined, { maximumFractionDigits: 0 })} L</strong>{" "}
                water, and <strong>{saveKgCo2.toFixed(2)} kg</strong> CO₂ (average grid).
              </div>
            ) : (
              <p className="text-muted-foreground">Select two models to compare savings.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Detailed metrics</CardTitle>
        </CardHeader>
        <CardContent>
          {selected.length === 0 ? (
            <p className="text-muted-foreground text-sm">No models selected.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead className="text-right">Wh/query</TableHead>
                  <TableHead className="text-right">Water ml/q</TableHead>
                  <TableHead className="text-right">CO₂ g/q</TableHead>
                  <TableHead className="text-right">Params</TableHead>
                  <TableHead className="text-right">Eco</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {selected.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell className="font-medium">{m.name}</TableCell>
                    <TableCell>{m.provider}</TableCell>
                    <TableCell className="text-right">
                      {m.energy_per_query_wh?.toFixed(4) ?? "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      {m.water_per_query_ml?.toFixed(2) ?? "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      {m.co2_per_query_g?.toFixed(3) ?? "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      {m.parameter_count?.toLocaleString() ?? "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <span
                        className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${ecoBadgeClass(m.eco_score)}`}
                      >
                        {m.eco_score ?? "—"}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
