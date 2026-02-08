"use client"

import { useState } from "react"
import { useRecommendationStore } from "@/features/recommendations/store"
import { MovieDetailModal } from "@/features/movies/components/MovieDetailModal"
import type { RecommendedMovie } from "@/features/recommendations/types"
import { RecommendationsEmpty } from "@/features/recommendations/components/RecommendationsEmpty"
import { RecommendationsError } from "@/features/recommendations/components/RecommendationsError"
import { RecommendationsGrid } from "@/features/recommendations/components/RecommendationsGrid"
import { PageTransition } from "@/shared/ui/motion/PageTransition"

export default function RecommendationsPage() {
  const { recommendations, error } = useRecommendationStore()
  const [selectedMovie, setSelectedMovie] = useState<RecommendedMovie | null>(
    null
  )
  const [isModalOpen, setIsModalOpen] = useState(false)

  const handleMovieClick = (movie: RecommendedMovie) => {
    setSelectedMovie(movie)
    setIsModalOpen(true)
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
      <div className="container py-section space-y-stack">
        <div className="space-y-tight">
          <p className="text-overline text-muted-foreground/70">
            Personalized for you
          </p>
          <h1 className="text-h1 font-semibold">Recommended for you</h1>
        </div>

        <RecommendationsGrid movies={recommendations} onSelect={handleMovieClick} />

        <MovieDetailModal
          movieId={selectedMovie?.movieId ?? null}
          tmdbId={selectedMovie?.tmdbId ?? null}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
        />
      </div>
    </PageTransition>
  )
}
