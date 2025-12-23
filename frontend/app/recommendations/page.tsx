"use client"

import { useRecommendationStore } from "@/lib/store/recommendationStore"
import { MovieCard } from "@/components/movie/MovieCard"

export default function RecommendationsPage() {
  const { results } = useRecommendationStore()

  return (
    <main className="px-10 py-8">
      <h1 className="mb-6 text-3xl font-bold">Your Recommendations</h1>

      <div className="grid grid-cols-6 gap-6">
        {results.map((m) => (
          <MovieCard key={m.movieId} movie={m} />
        ))}
      </div>
    </main>
  )
}
