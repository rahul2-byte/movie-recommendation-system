"use client"

import { useRecommendationStore } from "@/features/recommendations/store"
import { MovieCard } from "@/features/movies/components/MovieCard"
import Link from "next/link"
import { Button } from "@/shared/ui/Button"

export default function RecommendationsPage() {
  const { recommendations } = useRecommendationStore()

  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-150px)] text-center px-4">
        <h2 className="text-3xl font-bold text-foreground mb-4">
          No Recommendations Yet!
        </h2>
        <p className="text-lg text-muted-foreground mb-8 max-w-md">
          It looks like we don&apos;t have any movie recommendations for you at
          the moment. Head back to the homepage to tell us what you like!
        </p>
        <Link href="/">
          <Button size="lg">Get Movie Recommendations</Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="px-6 py-8">
      <h1 className="mb-6 text-2xl font-bold text-foreground">
        Recommended for You
      </h1>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {recommendations.map((movie) => (
          <MovieCard
            key={movie.tmdbId}
            movie={movie}
          />
        ))}
      </div>
    </div>
  )
}
