"use client"

import { MovieCard } from "@/features/movies/components/MovieCard"
import type { RecommendedMovie } from "@/features/recommendations/types"

export function RecommendationsGrid({
  movies,
  onSelect,
}: {
  movies: RecommendedMovie[]
  onSelect: (movie: RecommendedMovie) => void
}) {
  return (
    <div className="grid grid-cols-2 gap-grid sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {movies.map((movie, index) => (
        <MovieCard
          key={`${movie.movieId}-${index}`}
          movie={movie}
          onClick={() => onSelect(movie)}
        />
      ))}
    </div>
  )
}
