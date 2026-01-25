"use client"

import { useRecommendationStore } from "@/lib/store/recommendation"
import { MovieCard } from "@/components/movie/MovieCard"

export default function RecommendationsPage() {
  const { recommendations } = useRecommendationStore()

  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="p-6 text-gray-400">
        No recommendations found.
      </div>
    )
  }

  return (
    <div className="px-6 py-8">
      <h1 className="mb-6 text-2xl font-bold">
        Recommended for You
      </h1>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {recommendations.map((movie) => (
          <MovieCard
            key={movie.movieId}
            movie={movie}
          />
        ))}
      </div>
    </div>
  )
}
