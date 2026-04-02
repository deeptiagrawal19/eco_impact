"use client"

import * as React from "react"
import { ArrowDown, ArrowUp } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { pickModels } from "@/lib/dashboard-mocks"
import { useModels } from "@/lib/queries"
import { ecoBadgeClass } from "@/lib/eco-badge"
import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"

type SortKey =
  | "name"
  | "provider"
  | "energy"
  | "water"
  | "carbon"
  | "eco_score"

export function ModelEfficiencyTable() {
  const { data, isPending, isError } = useModels()
  const [sort, setSort] = React.useState<SortKey>("eco_score")
  const [dir, setDir] = React.useState<"asc" | "desc">("asc")

  const rows = React.useMemo(() => {
    const m = pickModels(data?.models, isError)
    const order = { A: 1, B: 2, C: 3, D: 4, F: 5 }
    const ecoRank = (s: string | null) =>
      order[(s ?? "Z").toUpperCase() as keyof typeof order] ?? 99
    return [...m].sort((a, b) => {
      let cmp = 0
      switch (sort) {
        case "name":
          cmp = a.name.localeCompare(b.name)
          break
        case "provider":
          cmp = a.provider.localeCompare(b.provider)
          break
        case "energy":
          cmp = (a.energy_per_query_wh ?? 0) - (b.energy_per_query_wh ?? 0)
          break
        case "water":
          cmp = (a.water_per_query_ml ?? 0) - (b.water_per_query_ml ?? 0)
          break
        case "carbon":
          cmp = (a.co2_per_query_g ?? 0) - (b.co2_per_query_g ?? 0)
          break
        case "eco_score":
          cmp = ecoRank(a.eco_score) - ecoRank(b.eco_score)
          break
        default:
          cmp = 0
      }
      return dir === "asc" ? cmp : -cmp
    })
  }, [data?.models, isError, sort, dir])

  const header = (key: SortKey, label: string) => (
    <TableHead>
      <button
        type="button"
        className="hover:text-foreground flex items-center gap-1 font-medium"
        onClick={() => {
          if (sort === key) setDir((d) => (d === "asc" ? "desc" : "asc"))
          else {
            setSort(key)
            setDir("asc")
          }
        }}
      >
        {label}
        {sort === key ? (
          dir === "asc" ? (
            <ArrowUp className="size-3" />
          ) : (
            <ArrowDown className="size-3" />
          )
        ) : null}
      </button>
    </TableHead>
  )

  if (isPending && !data?.models?.length) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            {header("name", "Model")}
            {header("provider", "Provider")}
            {header("energy", "Energy / query (Wh)")}
            {header("water", "Water / query (ml)")}
            {header("carbon", "CO₂ / query (g)")}
            {header("eco_score", "Eco-score")}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={r.id}>
              <TableCell className="font-medium">{r.name}</TableCell>
              <TableCell className="capitalize">{r.provider}</TableCell>
              <TableCell className="tabular-nums">
                {r.energy_per_query_wh != null
                  ? r.energy_per_query_wh.toFixed(3)
                  : "—"}
              </TableCell>
              <TableCell className="tabular-nums">
                {r.water_per_query_ml != null
                  ? r.water_per_query_ml.toFixed(2)
                  : "—"}
              </TableCell>
              <TableCell className="tabular-nums">
                {r.co2_per_query_g != null ? r.co2_per_query_g.toFixed(3) : "—"}
              </TableCell>
              <TableCell>
                <Badge
                  className={cn("font-mono text-xs", ecoBadgeClass(r.eco_score))}
                  variant="outline"
                >
                  {r.eco_score ?? "—"}
                </Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
