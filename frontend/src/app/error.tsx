"use client"

import { useEffect } from "react"
import { Button } from "@/shared/ui/Button"

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
    <div className="flex min-h-[80vh] flex-col items-center justify-center space-y-10 px-6 text-center">
      <div className="p-12 bg-destructive/10 rounded-[3rem] border-4 border-destructive/20 skew-y-1">
        <h2 className="text-6xl font-black uppercase tracking-tighter text-destructive">Technical Glitch</h2>
        <p className="mt-4 text-2xl text-muted-foreground font-bold italic">
          The film projector jammed. Hold tight while we fix it.
        </p>
      </div>
      
      <Button 
        onClick={() => reset()} 
        size="lg" 
        className="rounded-full px-12 h-16 text-xl font-black uppercase bg-foreground text-background hover:scale-110 transition-transform"
      >
        Restart Reel
      </Button>
    </div>
  )
}