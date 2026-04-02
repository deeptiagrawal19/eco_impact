import { NextRequest, NextResponse } from "next/server"

const API_BASE =
  process.env.API_URL?.replace(/\/$/, "") ?? "http://localhost:8000"

export async function POST(request: NextRequest) {
  const body = await request.text()
  const upstream = await fetch(`${API_BASE}/api/impact/estimate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body,
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
