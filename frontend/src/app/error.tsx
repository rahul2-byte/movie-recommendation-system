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
    // Log the error to an observability provider (e.g., Sentry)
    console.error("Uncaught App Error:", error)
  }, [error])

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background p-6 text-center">
      <div className="mb-6 rounded-full bg-error/10 p-4 text-error">
        <AlertCircle className="h-12 w-12" />
      </div>
      
      <h1 className="mb-2 font-serif text-3xl text-white">Something went sideways.</h1>
      <p className="mb-8 max-w-md text-text-secondary">
        An unexpected error occurred in our cinematic engine. We've been notified and are looking into it.
      </p>

      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          onClick={() => reset()}
          className="btn btn-primary"
        >
          <RotateCcw className="h-4 w-4" />
          Try Again
        </button>
        
        <Link href="/" className="btn btn-secondary">
          <Home className="h-4 w-4" />
          Back to Home
        </Link>
      </div>
      
      {error.digest && (
        <p className="mt-8 text-xs text-text-muted">Error ID: {error.digest}</p>
      )}
    </div>
  )
}