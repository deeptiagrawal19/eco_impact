export function ecoBadgeClass(score: string | null | undefined): string {
  const s = (score ?? "").toUpperCase()
  switch (s) {
    case "A":
      return "border border-emerald-500/40 bg-emerald-500/15 text-emerald-400"
    case "B":
      return "border border-lime-500/40 bg-lime-500/15 text-lime-400"
    case "C":
      return "border border-yellow-500/40 bg-yellow-500/15 text-yellow-400"
    case "D":
      return "border border-orange-500/40 bg-orange-500/15 text-orange-400"
    case "F":
      return "border border-red-500/40 bg-red-500/15 text-red-400"
    default:
      return "border border-muted bg-muted/30 text-muted-foreground"
  }
}
