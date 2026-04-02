"use client"

import * as React from "react"
import * as echarts from "echarts"
import ReactECharts from "echarts-for-react"

import type { DataCenter } from "@/lib/dashboard-queries"

const GEO_URL =
  "https://cdn.jsdelivr.net/npm/echarts@5.5.1/map/json/world.json"

type ScatterDatum = {
  name: string
  value: [number, number, number]
  provider: string
}

type Props = { dataCenters: DataCenter[] }

export function WaterStressMap({ dataCenters }: Props) {
  const [ready, setReady] = React.useState(false)

  React.useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch(GEO_URL)
        const geo = await res.json()
        if (cancelled) return
        echarts.registerMap("eco_world_water", geo)
        setReady(true)
      } catch {
        setReady(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const scatter = React.useMemo((): ScatterDatum[] => {
    return dataCenters
      .filter((d) => d.latitude != null && d.longitude != null)
      .map((d) => ({
        name: d.name ?? d.id,
        value: [d.longitude!, d.latitude!, d.water_stress_level ?? 0],
        provider: d.provider,
      }))
  }, [dataCenters])

  const option = React.useMemo(
    () => ({
      backgroundColor: "transparent",
      tooltip: {
        trigger: "item" as const,
        formatter: (p: { name?: string; data?: ScatterDatum }) => {
          const d = p.data
          if (!d) return p.name ?? ""
          const stress = d.value[2]
          return `${d.name}<br/>Provider: ${d.provider}<br/>Water stress index: ${stress.toFixed(1)} (WRI-style 0–5)`
        },
      },
      visualMap: {
        min: 0,
        max: 5,
        dimension: 2,
        text: ["High stress", "Low"],
        calculable: true,
        inRange: { color: ["#10b981", "#eab308", "#dc2626"] },
      },
      geo: ready
        ? {
            map: "eco_world_water",
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
          symbolSize: (val: [number, number, number]) =>
            12 + Math.min(18, (Number(val[2]) || 0) * 2),
          itemStyle: {
            borderColor: "#0f172a",
            borderWidth: 1,
          },
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
