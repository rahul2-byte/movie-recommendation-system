"use client"

import { useEffect } from "react"
import { Button } from "@/shared/ui/Button"
import { AlertTriangle } from "lucide-react"

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-gutter text-center space-y-stack">
      <div className="relative">
        <div className="absolute inset-0 bg-destructive/20 blur-3xl rounded-pill" />
        <AlertTriangle className="h-20 w-20 text-destructive relative z-10" strokeWidth={1} />
      </div>

      <div className="space-y-tight max-w-narrow z-10">
        <h2 className="text-h1 font-semibold">
          We hit a snag
        </h2>
        <p className="text-body text-muted-foreground">
          The projection booth ran into an issue. Please try again or reload the page.
        </p>
        <p className="text-caption text-muted-foreground/60 font-mono bg-surface px-card py-tight rounded-md">
          {error.message || "Unknown error"}
        </p>
      </div>

      <div className="flex flex-wrap gap-3 z-10">
        <Button onClick={() => window.location.reload()} variant="outline">
          Reload page
        </Button>
        <Button onClick={reset}>Try again</Button>
      </div>
    </div>
  )
}
