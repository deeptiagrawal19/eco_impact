"use client"

import "leaflet/dist/leaflet.css"

import * as React from "react"
import {
  Circle,
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
} from "react-leaflet"

import { useDashboardFilters } from "@/components/dashboard/filter-context"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { carbonIntensityColor, providerColor } from "@/lib/chart-palette"
import type { DataCenter } from "@/lib/dashboard-queries"
import { useCarbonByRegion, useDataCenters } from "@/lib/dashboard-queries"
import { pickCarbonByRegion, pickDataCenters } from "@/lib/dashboard-mocks"
import { REGION_LON_LAT } from "@/lib/region-coords"

type LayerMode = "providers" | "carbon" | "water"

function carbonForDc(
  dc: DataCenter,
  regions: { region: string; carbon_avg: number | null }[],
): number | null {
  const key = dc.grid_region ?? dc.region
  const hit = regions.find((r) => r.region === key)
  return hit?.carbon_avg ?? null
}

function stressFill(stress: number): string {
  const t = Math.min(1, Math.max(0, stress / 5))
  if (t < 0.33) return "#10b981"
  if (t < 0.66) return "#eab308"
  return "#dc2626"
}

export function DataCenterMap() {
  const { region: filterRegion } = useDashboardFilters()
  const {
    data: dcRes,
    isPending: dcP,
    isError: dcErr,
  } = useDataCenters()
  const {
    data: carbRes,
    isPending: cP,
    isError: cErr,
  } = useCarbonByRegion()
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => setMounted(true), [])

  const [layers, setLayers] = React.useState({
    carbon: true,
    water: true,
    dc: true,
  })
  const [layerMode, setLayerMode] = React.useState<LayerMode>("providers")

  const dcs = React.useMemo(() => {
    let rows = pickDataCenters(dcRes?.data_centers, dcErr)
    if (filterRegion)
      rows = rows.filter((d) => d.grid_region === filterRegion || d.region === filterRegion)
    return rows.filter((d) => d.latitude != null && d.longitude != null)
  }, [dcRes, dcErr, filterRegion])

  const carbRows = React.useMemo(
    () => pickCarbonByRegion(carbRes, cErr).regions,
    [carbRes, cErr],
  )

  const carbonOverlay = React.useMemo(() => {
    const features = carbRows
      .map((r) => {
        const ll = REGION_LON_LAT[r.region]
        if (!ll || r.carbon_avg == null) return null
        return {
          type: "Feature" as const,
          properties: { carbon: r.carbon_avg },
          geometry: {
            type: "Point" as const,
            coordinates: [ll[0], ll[1]] as [number, number],
          },
        }
      })
      .filter((x): x is NonNullable<typeof x> => Boolean(x))
    return { type: "FeatureCollection" as const, features }
  }, [carbRows])

  const waterOverlay = React.useMemo(() => {
    const features = dcs
      .map((dc) => {
        if (dc.water_stress_level == null) return null
        return {
          type: "Feature" as const,
          properties: { stress: dc.water_stress_level },
          geometry: {
            type: "Point" as const,
            coordinates: [dc.longitude!, dc.latitude!] as [number, number],
          },
        }
      })
      .filter((x): x is NonNullable<typeof x> => Boolean(x))
    return { type: "FeatureCollection" as const, features }
  }, [dcs])

  const markerColor = React.useCallback(
    (dc: DataCenter): string => {
      if (layerMode === "providers") return providerColor(dc.provider)
      if (layerMode === "carbon") {
        const g = carbonForDc(dc, carbRows)
        return g != null ? carbonIntensityColor(g) : "#64748b"
      }
      const s = dc.water_stress_level
      if (s == null) return "#64748b"
      const t = Math.min(1, Math.max(0, s / 5))
      return `hsl(${120 - t * 100}, 70%, 45%)`
    },
    [layerMode, carbRows],
  )

  const sizeFor = React.useCallback((dc: DataCenter) => {
    const mw = dc.capacity_mw ?? 10
    return Math.max(10, Math.min(44, 12 + Math.sqrt(mw) * 3))
  }, [])

  const loading =
    !mounted ||
    (dcP && !dcRes?.data_centers?.length) ||
    (cP && !carbRes?.regions?.some((r) => r.carbon_avg != null))
  if (loading) {
    return <Skeleton className="h-[calc(100vh-8rem)] w-full rounded-xl" />
  }

  return (
    <div className="relative h-[calc(100vh-8rem)] min-h-[480px] w-full overflow-hidden rounded-xl border">
      <div className="bg-card/95 absolute left-3 top-3 z-[1000] flex max-w-[min(100%-1.5rem,380px)] flex-col gap-2 rounded-lg border p-3 text-xs shadow-md backdrop-blur">
        <div className="font-medium">Layers</div>
        <div className="flex flex-wrap gap-2">
          {(
            [
              ["dc", "Data centers"],
              ["carbon", "Carbon overlay"],
              ["water", "Water stress"],
            ] as const
          ).map(([k, label]) => (
            <Button
              key={k}
              type="button"
              variant={layers[k] ? "secondary" : "outline"}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setLayers((s) => ({ ...s, [k]: !s[k] }))}
            >
              {label}
            </Button>
          ))}
        </div>
        <div className="text-muted-foreground pt-1">Marker coloring</div>
        <div className="flex flex-wrap gap-2">
          {(
            [
              ["providers", "By provider"],
              ["carbon", "By grid carbon"],
              ["water", "By water stress"],
            ] as const
          ).map(([k, label]) => (
            <Button
              key={k}
              type="button"
              variant={layerMode === k ? "default" : "outline"}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setLayerMode(k)}
            >
              {label}
            </Button>
          ))}
        </div>
        <p className="text-muted-foreground pt-1 text-[10px] leading-tight">
          Basemap: OpenStreetMap (no API key). Overlays match prior Mapbox styling.
        </p>
      </div>

      <MapContainer
        center={[22, 2]}
        zoom={2}
        minZoom={2}
        maxZoom={18}
        className="z-0 h-full w-full rounded-lg [&_.leaflet-control-zoom]:mt-14"
        scrollWheelZoom
        worldCopyJump
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {layers.carbon &&
          carbonOverlay.features.map((f, i) => {
            const [lon, lat] = f.geometry.coordinates
            const carbon = f.properties.carbon as number
            const fill = carbonIntensityColor(carbon)
            return (
              <Circle
                key={`carbon-${i}`}
                center={[lat, lon]}
                radius={420_000}
                pathOptions={{
                  fillColor: fill,
                  fillOpacity: 0.28,
                  color: fill,
                  weight: 1,
                  opacity: 0.35,
                }}
              />
            )
          })}
        {layers.water &&
          waterOverlay.features.map((f, i) => {
            const [lon, lat] = f.geometry.coordinates
            const stress = f.properties.stress as number
            const fill = stressFill(stress)
            return (
              <Circle
                key={`water-${i}`}
                center={[lat, lon]}
                radius={260_000}
                pathOptions={{
                  fillColor: fill,
                  fillOpacity: 0.22,
                  color: fill,
                  weight: 1,
                  opacity: 0.3,
                }}
              />
            )
          })}
        {layers.dc &&
          dcs.map((dc) => (
            <CircleMarker
              key={dc.id}
              center={[dc.latitude!, dc.longitude!]}
              radius={Math.max(6, sizeFor(dc) / 2)}
              pathOptions={{
                color: "#0f172a",
                weight: 2,
                fillColor: markerColor(dc),
                fillOpacity: 0.95,
              }}
            >
              <Popup className="[&_.leaflet-popup-content-wrapper]:bg-popover [&_.leaflet-popup-content-wrapper]:text-popover-foreground [&_.leaflet-popup-content]:!m-3 [&_.leaflet-popup-content]:text-xs [&_.leaflet-popup-tip]:bg-popover">
                <div className="space-y-1">
                  <div className="font-semibold">{dc.name ?? dc.id}</div>
                  <div>Provider: {dc.provider}</div>
                  <div>Region: {dc.region}</div>
                  {dc.pue != null && <div>PUE: {dc.pue.toFixed(2)}</div>}
                  {dc.renewable_percentage != null && (
                    <div>Renewable match: {dc.renewable_percentage.toFixed(0)}%</div>
                  )}
                  <div>
                    Grid carbon:{" "}
                    {carbonForDc(dc, carbRows) != null
                      ? `${carbonForDc(dc, carbRows)!.toFixed(0)} g/kWh`
                      : "—"}
                  </div>
                  <div>
                    Water stress:{" "}
                    {dc.water_stress_level != null
                      ? `${dc.water_stress_level.toFixed(1)} / 5`
                      : "—"}
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          ))}
      </MapContainer>
    </div>
  )
}
