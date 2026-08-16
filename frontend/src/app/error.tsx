"use client"

import { useEffect } from "react"
import Link from "next/link"
import { AlertCircle, RotateCcw, Home } from "lucide-react"

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error("Uncaught App Error:", error)
  }, [error])

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-ink p-6 text-center">
      <div className="mb-6 grid size-20 place-items-center rounded-full bg-danger/10 text-danger">
        <AlertCircle className="h-12 w-12" />
      </div>

      <h1 className="mb-2 font-display text-3xl text-paper">
        Something went sideways.
      </h1>
      <p className="mb-8 max-w-md text-muted">
        An unexpected error interrupted this page. Try again, or return home and
        continue browsing.
      </p>

      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          onClick={() => reset()}
          className="inline-flex min-h-11 items-center justify-center gap-2 bg-crimson px-4 text-sm font-bold text-white transition-colors hover:bg-crimson-bright"
        >
          <RotateCcw className="h-4 w-4" />
          Try Again
        </button>

        <Link
          href="/"
          className="inline-flex min-h-11 items-center justify-center gap-2 border border-line bg-panel px-4 text-sm font-bold text-paper transition-colors hover:border-muted"
        >
          <Home className="h-4 w-4" />
          Back to Home
        </Link>
      </div>

      {error.digest && (
        <p className="mt-8 text-xs text-dim">Error ID: {error.digest}</p>
      )}
    </div>
  )
}
