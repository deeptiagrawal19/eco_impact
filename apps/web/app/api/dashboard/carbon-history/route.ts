import { NextRequest, NextResponse } from "next/server"
import { fetchFromApi } from "@/lib/server-api"

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.toString()
  const r = await fetchFromApi(`/api/dashboard/carbon-history${q ? `?${q}` : ""}`)
  const t = await r.text()
  return new NextResponse(t, {
    status: r.status,
    headers: { "Content-Type": r.headers.get("content-type") ?? "application/json" },
  })
}
