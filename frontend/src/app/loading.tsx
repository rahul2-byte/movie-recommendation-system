import { Loader2 } from "lucide-react"

export default function Loading() {
  return (
    <div className="flex min-h-[60vh] w-full items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-crimson" />
        <p className="animate-pulse font-display text-lg text-dim">
          Loading the archive...
        </p>
      </div>
    </div>
  )
}
