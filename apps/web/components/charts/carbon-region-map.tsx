"use client"

import * as React from "react"
import * as echarts from "echarts"
import ReactECharts from "echarts-for-react"

import type { CarbonByRegion } from "@/lib/dashboard-queries"
import { REGION_LON_LAT } from "@/lib/region-coords"

const GEO_URL =
  "https://cdn.jsdelivr.net/npm/echarts@5.5.1/map/json/world.json"

type Props = { data: CarbonByRegion | undefined }

export function CarbonRegionMap({ data }: Props) {
  const [ready, setReady] = React.useState(false)

  React.useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch(GEO_URL)
        const geo = await res.json()
        if (cancelled) return
        echarts.registerMap("eco_world", geo)
        setReady(true)
      } catch {
        setReady(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const scatter = React.useMemo(() => {
    const rows = data?.regions ?? []
    return rows
      .map((r) => {
        const ll = REGION_LON_LAT[r.region]
        if (!ll || r.carbon_avg == null) return null
        return {
          name: r.region,
          value: [...ll, r.carbon_avg] as [number, number, number],
        }
      })
      .filter(Boolean) as { name: string; value: [number, number, number] }[]
  }, [data])

  const option = React.useMemo(
    () => ({
      backgroundColor: "transparent",
      tooltip: {
        trigger: "item" as const,
        formatter: (p: { name?: string; value?: number[] }) => {
          const v = p.value
          if (Array.isArray(v) && v[2] != null)
            return `${p.name}<br/>${v[2].toFixed(0)} gCO₂/kWh`
          return p.name ?? ""
        },
      },
      visualMap: {
        min: 200,
        max: 550,
        dimension: 2,
        text: ["High", "Low"],
        realtime: true,
        calculable: true,
        inRange: {
          color: ["#10b981", "#eab308", "#ef4444"],
        },
      },
      geo: ready
        ? {
            map: "eco_world",
            roam: true,
            emphasis: { label: { show: false } },
            itemStyle: {
              areaColor: "#1e293b",
              borderColor: "#334155",
            },
          }
        : undefined,
      series: [
        {
          type: "scatter" as const,
          coordinateSystem: ready ? ("geo" as const) : undefined,
          symbolSize: (val: number[]) =>
            14 + Math.min(22, Number(val[2] ?? 0) / 22),
          data: scatter,
        },
      ],
    }),
    [ready, scatter],
  )

  if (!ready) {
    return (
      <div className="text-muted-foreground flex h-[420px] items-center justify-center rounded-lg border border-dashed text-sm">
        Loading world map…
      </div>
    )
  }

  return (
    <div className="h-[420px] w-full">
      <ReactECharts
        option={option}
        style={{ height: "100%", width: "100%" }}
        notMerge
      />
    </div>
  )
}
