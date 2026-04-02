import { NextResponse } from "next/server"
import { fetchFromApi } from "@/lib/server-api"

export async function GET() {
  const r = await fetchFromApi("/api/gpu/benchmarks")
  const t = await r.text()
  return new NextResponse(t, {
    status: r.status,
    headers: { "Content-Type": r.headers.get("content-type") ?? "application/json" },
  })
}
