"use client"

import type * as React from "react"
import { TrendingDown, TrendingUp } from "lucide-react"
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts"

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { cn } from "@/lib/utils"

type SparkPoint = { t: string; value: number }

export function MetricCard({
  title,
  valueLabel,
  trendPct,
  sparkline,
  valueClassName,
  valueStyle,
}: {
  title: string
  valueLabel: string
  trendPct: number | null | undefined
  sparkline: SparkPoint[]
  valueClassName?: string
  valueStyle?: React.CSSProperties
}) {
  const up = trendPct != null && trendPct > 0
  const down = trendPct != null && trendPct < 0
  const chartData = sparkline.map((p, i) => ({
    i,
    v: p.value,
  }))

  return (
    <Card className="overflow-hidden border-border/80 bg-card/50">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <CardTitle className="text-muted-foreground text-sm font-medium">
          {title}
        </CardTitle>
        {trendPct != null && (
          <span
            className={cn(
              "flex items-center gap-1 text-xs font-medium tabular-nums",
              up && "text-amber-500",
              down && "text-emerald-500",
              !up && !down && "text-muted-foreground",
            )}
          >
            {up ? <TrendingUp className="size-3" /> : null}
            {down ? <TrendingDown className="size-3" /> : null}
            {trendPct > 0 ? "+" : ""}
            {trendPct.toFixed(1)}%
          </span>
        )}
      </CardHeader>
      <CardContent>
        <div
          className={cn(
            "text-2xl font-semibold tracking-tight md:text-3xl",
            valueClassName,
          )}
          style={valueStyle}
        >
          {valueLabel}
        </div>
        <div className="mt-3 h-12 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(v) => [Number(v ?? 0).toFixed(3), ""]}
              />
              <Line
                type="monotone"
                dataKey="v"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
