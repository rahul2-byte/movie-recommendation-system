"use client"

import { useState } from "react"
import { useRecommendationStore } from "@/features/recommendations/store"
import { MovieCard } from "@/features/movies/components/MovieCard"
import Link from "next/link"
import { Button } from "@/shared/ui/Button"
import { MovieDetailModal } from "@/features/movies/components/MovieDetailModal"
import { RecommendedMovie } from "@/features/recommendations/types"
import { AlertCircle, RefreshCw } from "lucide-react"

export default function RecommendationsPage() {
  const { recommendations, error } = useRecommendationStore()
  const [selectedMovie, setSelectedMovie] = useState<RecommendedMovie | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const handleMovieClick = (movie: RecommendedMovie) => {
    setSelectedMovie(movie)
    setIsModalOpen(true)
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-150px)] text-center px-4 space-y-6">
        <div className="p-4 bg-destructive/10 rounded-full mb-4">
          <AlertCircle className="w-12 h-12 text-destructive" />
        </div>
        <h2 className="text-3xl md:text-4xl font-black uppercase italic tracking-tighter text-white/90">
          System <span className="text-destructive">Error</span>
        </h2>
        <p className="text-sm font-bold uppercase tracking-widest text-white/40 max-w-md leading-relaxed">
          {error.includes("fetch") || error.includes("connect") 
            ? "Unable to connect to the discovery engine. The backend might be offline." 
            : "An unexpected error occurred while generating your reel."}
        </p>
        <div className="flex gap-4 mt-8">
            <Link href="/">
                <Button variant="outline" size="lg" className="font-bold uppercase tracking-widest">
                    Try Again
                </Button>
            </Link>
        </div>
      </div>
    )
  }

  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-150px)] text-center px-4 space-y-6">
        <h2 className="text-4xl md:text-5xl font-black uppercase italic tracking-tighter text-white/90">
          No <span className="text-primary">Recommendations</span> Yet
        </h2>
        <p className="text-sm font-bold uppercase tracking-widest text-white/40 max-w-md">
          It looks like we don&apos;t have any movie recommendations for you at
          the moment.
        </p>
        <Link href="/">
          <Button size="lg" className="mt-4 font-black uppercase tracking-widest">
            Start Discovery
          </Button>
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
        {recommendations.map((movie, index) => (
          <MovieCard
            key={`${movie.movieId}-${index}`}
            movie={movie}
            onClick={() => handleMovieClick(movie)}
          />
        ))}
      </div>

      <MovieDetailModal 
        movie={selectedMovie}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  )
}
