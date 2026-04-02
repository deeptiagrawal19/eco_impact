import { NextResponse } from "next/server"

const API_BASE =
  process.env.API_URL?.replace(/\/$/, "") ?? "http://localhost:8000"

export async function GET() {
  const upstream = await fetch(`${API_BASE}/api/impact/models`, {
    headers: { Accept: "application/json" },
    next: { revalidate: 60 },
  })
  const text = await upstream.text()
  const ct =
    upstream.headers.get("content-type") ?? "application/json; charset=utf-8"
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": ct },
  })
}
