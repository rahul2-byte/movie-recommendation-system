"use client"

import Link from "next/link"
import { ArrowLeft, RefreshCw } from "lucide-react"
import { useRecommendationStore } from "@/features/recommendations/store"
import { useRecommendations } from "@/features/recommendations/hooks/useRecommendations"
import { RecommendationsEmpty } from "@/features/recommendations/components/RecommendationsEmpty"
import { RecommendationsError } from "@/features/recommendations/components/RecommendationsError"
import { RecommendationsGrid } from "@/features/recommendations/components/RecommendationsGrid"

export default function RecommendationsPage() {
  const recommendations = useRecommendationStore(
    (state) => state.recommendations
  )
  const error = useRecommendationStore((state) => state.error)
  const sessionId = useRecommendationStore(
    (state) => state.recommendationSessionId
  )
  const nextOffset = useRecommendationStore(
    (state) => state.recommendationNextOffset
  )
  const hasMore = useRecommendationStore((state) => state.recommendationHasMore)
  const selectedMovies = useRecommendationStore((state) => state.selectedMovies)
  const { mutate, isPending } = useRecommendations()

  const refresh = () => {
    mutate({
      seed_tmdb_ids: selectedMovies.map((movie) => movie.tmdbId),
      limit: 200,
      refresh_seed: Date.now(),
    })
  }

  if (error) return <RecommendationsError message={error} />
  if (!recommendations.length) return <RecommendationsEmpty />

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12 sm:px-10 lg:py-20">
      <div>
        <Link
          href="/#build-lineup"
          className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson inline-flex items-center gap-2 text-sm font-semibold text-muted transition-colors hover:text-paper"
        >
          <ArrowLeft className="h-4 w-4" /> Edit lineup
        </Link>
        <header className="mt-12 flex flex-col gap-7 border-b border-line pb-10 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <span className="text-sm font-semibold text-crimson">
              Inspired by{" "}
              {selectedMovies.map((movie) => movie.title).join(", ")}
            </span>
            <h1 className="mt-2 font-display text-5xl leading-[0.95] text-paper sm:text-7xl">
              Your ranked lineup
            </h1>
            <p className="mt-4 max-w-2xl text-lg leading-8 text-muted">
              Explore the results or return to your film strip to change the
              direction.
            </p>
          </div>
          <button
            className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-line bg-panel px-5 text-sm font-bold text-paper transition-colors hover:border-muted active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
            onClick={refresh}
            disabled={isPending}
          >
            <RefreshCw
              className={`h-4 w-4 ${isPending ? "animate-spin" : ""}`}
            />
            {isPending ? "Finding movies…" : "Refresh lineup"}
          </button>
        </header>
        <RecommendationsGrid
          movies={recommendations}
          sessionId={sessionId}
          nextOffset={nextOffset}
          hasMore={hasMore}
        />
      </div>
    </div>
  )
}
