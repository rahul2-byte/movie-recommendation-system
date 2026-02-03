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
    // Log the error to an error reporting service
    console.error(error)
  }, [error])

  return (
    <div className="flex min-h-[calc(100vh-80px)] flex-col items-center justify-center p-4 text-center space-y-8">
      <div className="relative">
        <div className="absolute inset-0 bg-destructive/20 blur-3xl rounded-full" />
        <AlertTriangle className="h-24 w-24 text-destructive relative z-10" strokeWidth={1} />
      </div>

      <div className="space-y-4 max-w-lg z-10">
        <h2 className="text-4xl font-black uppercase italic tracking-tighter text-white">
          Technical <span className="text-destructive">Difficulties</span>
        </h2>
        <p className="text-muted-foreground font-medium text-sm uppercase tracking-widest leading-relaxed">
          We encountered a connection error with the projection booth. Please try reloading the scene.
        </p>
        <p className="text-xs text-white/20 font-mono bg-black/40 p-2 rounded">
            {error.message || "Unknown Error"}
        </p>
      </div>

      <div className="flex gap-4 z-10">
        <Button 
            onClick={() => window.location.reload()} 
            variant="outline"
            className="font-bold uppercase tracking-widest border-white/10 hover:bg-white/5"
        >
          Reload Page
        </Button>
        <Button 
            onClick={reset}
            className="font-bold uppercase tracking-widest bg-primary text-primary-foreground hover:bg-primary/90"
        >
          Try Again
        </Button>
      </div>
    </div>
  )
}
