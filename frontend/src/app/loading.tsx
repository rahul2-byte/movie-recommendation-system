import { Skeleton } from "@/shared/ui/Skeleton"

export default function Loading() {
  return (
    <div className="container py-page space-y-section">
      <section className="min-h-screen w-full rounded-xl bg-surface-strong animate-pulse" />

      <div className="space-y-stack">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="space-y-tight">
            <Skeleton className="h-8 w-48" />
            <div className="flex gap-grid overflow-hidden">
              {[...Array(6)].map((_, j) => (
                <Skeleton
                  key={j}
                  className="aspect-poster w-poster shrink-0 rounded-card"
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
