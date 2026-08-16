"use client"

import { useEffect, useRef, useState } from "react"
import { MovieCard } from "@/features/movies/components/MovieCard"
import type { RecommendedMovie } from "@/features/recommendations/types"
import { fetchRecommendationPage } from "@/features/recommendations/api/recommendations"
import { useRecommendationStore } from "@/features/recommendations/store"

export function RecommendationsGrid({
  movies,
  sessionId,
  nextOffset,
  hasMore,
}: {
  movies: RecommendedMovie[]
  sessionId: string | null
  nextOffset: number | null
  hasMore: boolean
}) {
  const appendRecommendationPage = useRecommendationStore(
    (state) => state.appendRecommendationPage
  )
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const sentinelRef = useRef<HTMLDivElement>(null)

  const loadMore = async () => {
    if (!sessionId || nextOffset === null || !hasMore || loading) return
    setLoading(true)
    setLoadError(null)
    try {
      appendRecommendationPage(
        await fetchRecommendationPage(sessionId, nextOffset)
      )
    } catch (error) {
      setLoadError(
        error instanceof Error ? error.message : "Could not load more movies."
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel || !hasMore || typeof IntersectionObserver === "undefined") {
      return
    }
    const observer = new IntersectionObserver(
      ([entry]) => entry.isIntersecting && void loadMore(),
      { rootMargin: "600px" }
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  })

  return (
    <>
      <div className="grid grid-cols-2 gap-x-3 gap-y-8 sm:grid-cols-3 sm:gap-x-4 lg:grid-cols-5 xl:grid-cols-6">
        {movies
          .filter((movie) => movie.posterUrl)
          .map((movie) => (
            <MovieCard
              key={movie.tmdbId}
              movie={{
                ...movie,
                year: movie.year ?? null,
                posterUrl: movie.posterUrl ?? null,
                rating: movie.rating ?? null,
                voteAverage: movie.rating ?? null,
                overview: movie.overview ?? null,
                movieId: movie.tmdbId,
              }}
            />
          ))}
      </div>
      <div ref={sentinelRef} className="mt-10 grid min-h-16 place-items-center">
        {loading ? (
          <div
            className="size-7 animate-spin rounded-full border-2 border-line border-t-crimson"
            aria-label="Loading more recommendations"
          />
        ) : hasMore ? (
          <button
            type="button"
            onClick={loadMore}
            className="min-h-11 border border-line px-4 text-sm font-bold text-paper hover:border-muted"
          >
            Load more
          </button>
        ) : null}
        {loadError ? (
          <p className="mt-3 text-sm text-danger">{loadError}</p>
        ) : null}
      </div>
    </>
  )
}
