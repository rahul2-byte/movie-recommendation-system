import { MovieRowSkeleton } from "@/features/movies/components/MovieRowSkeleton"
import { Skeleton } from "@/shared/ui/Skeleton"

/**
 * Global loading UI for the root layout.
 * Provides a skeleton screen that mimics the HomePage structure.
 */
export default function RootLoading() {
  return (
    <div className="container py-page space-y-section">
      {/* Hero Skeleton */}
      <section className="relative h-[70vh] min-h-[500px] w-full overflow-hidden rounded-3xl bg-surface p-gutter flex flex-col justify-end space-y-stack">
        <div className="space-y-tight max-w-narrow relative z-10">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-3/4" />
          <div className="pt-4 flex gap-3">
            <Skeleton className="h-12 w-40 rounded-pill" />
            <Skeleton className="h-12 w-12 rounded-full" />
          </div>
        </div>
      </section>

      {/* Highlights Skeleton */}
      <section className="space-y-stack">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="space-y-tight max-w-narrow">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-10 w-full" />
          </div>
          <Skeleton className="h-6 w-64 hidden md:block" />
        </div>

        <div className="grid gap-grid md:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="surface rounded-xl p-card space-y-tight">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-12 w-full" />
            </div>
          ))}
        </div>
      </section>

      {/* Catalog Rows Skeleton */}
      <div className="space-y-section pb-section">
        <MovieRowSkeleton title="Trending now" />
        <MovieRowSkeleton title="Popular hits" />
        <MovieRowSkeleton title="Fresh arrivals" />
      </div>
    </div>
  )
}