const base = () =>
  (
    process.env.NEXT_PUBLIC_API_URL ??
    process.env.API_URL ??
    "http://localhost:8000"
  ).replace(/\/$/, "")

export async function fetchFromApi(path: string, init?: RequestInit) {
  const url = path.startsWith("http") ? path : `${base()}${path}`
  return fetch(url, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
    next: { revalidate: 0 },
  })
}
