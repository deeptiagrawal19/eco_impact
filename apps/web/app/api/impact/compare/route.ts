import { NextRequest, NextResponse } from "next/server"

const API_BASE =
  process.env.API_URL?.replace(/\/$/, "") ?? "http://localhost:8000"

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.toString()
  const path = q ? `/api/impact/compare?${q}` : "/api/impact/compare"
  const upstream = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
    next: { revalidate: 0 },
  })
  const text = await upstream.text()
  const ct =
    upstream.headers.get("content-type") ?? "application/json; charset=utf-8"
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": ct },
  })
}
