"use client"

import * as React from "react"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

import { Button } from "@/components/ui/button"

export function ThemeToggle() {
  const { setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => setMounted(true), [])

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="relative size-9"
      aria-label="Toggle theme"
      onClick={() => {
        if (!mounted) return
        setTheme(resolvedTheme === "dark" ? "light" : "dark")
      }}
    >
      {!mounted ? (
        <Sun className="text-muted-foreground size-4" aria-hidden />
      ) : (
        <>
          <Sun className="size-4 scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
          <Moon className="absolute inset-0 m-auto size-4 scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
        </>
      )}
    </Button>
  )
}
