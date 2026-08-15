"use client"

import { useState } from "react"
import { useRecommendationStore } from "@/features/recommendations/store"
import { useRecommendations } from "@/features/recommendations/hooks/useRecommendations"
import { MovieDetailModal } from "@/features/movies/components/MovieDetailModal"
import type { RecommendedMovie } from "@/features/recommendations/types"
import { RecommendationsEmpty } from "@/features/recommendations/components/RecommendationsEmpty"
import { RecommendationsError } from "@/features/recommendations/components/RecommendationsError"
import { RecommendationsGrid } from "@/features/recommendations/components/RecommendationsGrid"
import { PageTransition } from "@/shared/ui/motion/PageTransition"
import Link from "next/link"
import { ArrowLeft, RefreshCw } from "lucide-react"
import type { Mood } from "@/features/recommendations/types"

export default function RecommendationsPage() {
  const recommendations = useRecommendationStore(
    (state) => state.recommendations
  )
  const error = useRecommendationStore((state) => state.error)
  const selectedMovies = useRecommendationStore((state) => state.selectedMovies)
  const selectedGenres = useRecommendationStore((state) => state.selectedGenres)

  const { mutate, isPending: isRefreshing } = useRecommendations()
  const [selectedMovie, setSelectedMovie] = useState<RecommendedMovie | null>(
    null
  )
  const [isModalOpen, setIsModalOpen] = useState(false)

  const handleMovieClick = (movie: RecommendedMovie) => {
    setSelectedMovie(movie)
    setIsModalOpen(true)
  }

  const handleRefresh = () => {
    const seedTmdbIds = selectedMovies.map((m) => m.tmdbId)
    mutate({
      seed_tmdb_ids: seedTmdbIds,
      moods: selectedGenres as Mood[],
      limit: 20,
    })
  }

  if (error) {
    return (
      <PageTransition>
        <RecommendationsError message={error} />
      </PageTransition>
    )
  }

  if (!recommendations || recommendations.length === 0) {
    return (
      <PageTransition>
        <RecommendationsEmpty />
      </PageTransition>
    )
  }

  return (
    <PageTransition>
      <div className="section pt-32 min-h-screen">
        <div className="container">
          <Link
            href="/setup"
            className="inline-flex items-center gap-2 text-text-muted hover:text-accent transition-colors mb-8 text-sm"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Curation
          </Link>

          <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-12 gap-6">
            <div className="flex flex-col gap-2 max-w-2xl">
              <span className="label-accent leading-relaxed">
                Based on: {selectedMovies.map((m) => m.title).join(", ")}
              </span>
              <h1 className="heading-section">Your Curated Lineup</h1>
              {selectedGenres.length > 0 && (
                <p className="text-italic text-text-muted">
                  {selectedGenres.join(", ")}
                </p>
              )}
            </div>

            <div className="flex gap-3">
              <button
                className="btn btn-secondary"
                onClick={handleRefresh}
                disabled={isRefreshing}
              >
                <RefreshCw
                  className={`btn-icon ${isRefreshing ? "animate-spin" : ""}`}
                />
                {isRefreshing ? "Thinking..." : "Refresh"}
              </button>
            </div>
          </div>

          <RecommendationsGrid
            movies={recommendations}
            onSelect={handleMovieClick}
          />

          <MovieDetailModal
            movieId={null}
            tmdbId={selectedMovie?.tmdbId ?? null}
            isOpen={isModalOpen}
            onClose={() => setIsModalOpen(false)}
          />
        </div>
      </div>
    </PageTransition>
  )
}
