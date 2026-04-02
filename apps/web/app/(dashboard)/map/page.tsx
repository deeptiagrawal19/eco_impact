"use client"

import { DataCenterMap } from "@/components/dashboard/data-center-map"

export default function GeographicMapPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Geographic view</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Facilities, grid-carbon halos, and water-stress halos over OpenStreetMap (no
          API key).
        </p>
      </div>
      <DataCenterMap />
    </div>
  )
}
