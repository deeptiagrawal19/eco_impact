import { NextRequest, NextResponse } from "next/server"

const API_BASE =
  process.env.API_URL?.replace(/\/$/, "") ?? "http://localhost:8000"

const CACHE_HEADERS = {
  "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300",
}

/**
 * BFF proxy to FastAPI ``/api/carbon/*``.
 *
 * Query ``op`` selects the upstream path:
 * - ``latest`` — requires ``region``
 * - ``history`` — requires ``region``, optional ``hours`` (default 24)
 * - ``regions`` — list MVP regions + latest row
 * - ``comparison`` — cross-region snapshot
 */
export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl
  const op = searchParams.get("op")

  if (!op) {
    return NextResponse.json(
      {
        error:
          "Missing op. Use op=latest|history|regions|comparison (see route docstring).",
      },
      { status: 400 },
    )
  }

  let target = ""

  if (op === "latest") {
    const region = searchParams.get("region")
    if (!region) {
      return NextResponse.json(
        { error: "latest requires region query param" },
        { status: 400 },
      )
    }
    target = `/api/carbon/latest?region=${encodeURIComponent(region)}`
  } else if (op === "history") {
    const region = searchParams.get("region")
    if (!region) {
      return NextResponse.json(
        { error: "history requires region query param" },
        { status: 400 },
      )
    }
    const hours = searchParams.get("hours") ?? "24"
    target = `/api/carbon/history?region=${encodeURIComponent(region)}&hours=${encodeURIComponent(hours)}`
  } else if (op === "regions") {
    target = "/api/carbon/regions"
  } else if (op === "comparison") {
    target = "/api/carbon/comparison"
  } else {
    return NextResponse.json(
      { error: `Unknown op: ${op}` },
      { status: 400 },
    )
  }

  const upstream = await fetch(`${API_BASE}${target}`, {
    headers: { Accept: "application/json" },
    next: { revalidate: 60 },
  })

  const body = await upstream.text()
  const ct =
    upstream.headers.get("content-type") ?? "application/json; charset=utf-8"

  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      ...CACHE_HEADERS,
      "Content-Type": ct,
    },
  })
}
