"use client"

import { useEffect, useRef, useState } from "react"
import { CatalogGrid } from "./CatalogGrid"
import type { Movie } from "../types/movie"
import {
  discoverMovies,
  getNewReleases,
  getPopularMovies,
  getTrendingMovies,
  type DiscoverFilters,
} from "../api"
import { getSimilarMovies, searchMovies } from "../api/movies"

type Source = "trending" | "popular" | "new" | "discover" | "search" | "similar"

export function InfiniteCatalogGrid({
  initialMovies,
  source,
  filters = {},
  query,
  tmdbId,
}: {
  initialMovies: Movie[]
  source: Source
  filters?: DiscoverFilters
  query?: string
  tmdbId?: number
}) {
  const [movies, setMovies] = useState(
    initialMovies.filter((movie) => movie.posterUrl)
  )
  const [page, setPage] = useState(2)
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(initialMovies.length > 0)
  const sentinelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setMovies(initialMovies.filter((movie) => movie.posterUrl))
    setPage(2)
    setHasMore(initialMovies.length > 0)
  }, [initialMovies])

  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel || !hasMore || typeof IntersectionObserver === "undefined") {
      return
    }
    const observer = new IntersectionObserver(
      async ([entry]) => {
        if (!entry.isIntersecting || loading) return
        setLoading(true)
        try {
          const next =
            source === "discover"
              ? await discoverMovies({ ...filters, page, limit: 24 })
              : source === "search" && query
                ? await searchMovies(query, page, 24)
                : source === "similar" && tmdbId
                  ? await getSimilarMovies(tmdbId, 24, page)
                  : source === "popular"
                    ? await getPopularMovies(24, page)
                    : source === "new"
                      ? await getNewReleases(24, page)
                      : await getTrendingMovies(24, page)
          const valid = next.filter((movie) => movie.posterUrl)
          setMovies((current) => {
            const seen = new Set(current.map((movie) => movie.tmdbId))
            return [
              ...current,
              ...valid.filter((movie) => !seen.has(movie.tmdbId)),
            ]
          })
          setPage((current) => current + 1)
          setHasMore(next.length > 0)
        } finally {
          setLoading(false)
        }
      },
      { rootMargin: "600px" }
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [filters, hasMore, loading, page, query, source, tmdbId])

  return (
    <>
      <CatalogGrid movies={movies} />
      <div
        ref={sentinelRef}
        className="grid min-h-24 place-items-center"
        aria-live="polite"
      >
        {loading ? (
          <div
            className="size-8 animate-spin rounded-full border-2 border-line border-t-crimson"
            aria-label="Loading more movies"
          />
        ) : null}
      </div>
    </>
  )
}
