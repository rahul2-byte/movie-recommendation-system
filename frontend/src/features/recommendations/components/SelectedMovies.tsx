"use client"

import { useRecommendationStore } from "@/features/recommendations/store"
import { LazyMotion, domAnimation, m, AnimatePresence } from "framer-motion"
import { Trash2 } from "lucide-react"
import { MovieCard } from "@/features/movies/components/MovieCard"

export function SelectedMovies() {
  const { selectedMovies, removeMovie, clearMovies } = useRecommendationStore()

  if (selectedMovies.length === 0) return null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
         <h2 className="heading-section text-2xl">Your Selection</h2>
         <button 
           onClick={clearMovies}
           className="text-sm text-text-muted hover:text-error transition-colors flex items-center gap-2"
         >
           <Trash2 className="w-4 h-4" /> Clear All
         </button>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6">
        <LazyMotion features={domAnimation} strict>
          <AnimatePresence>
            {selectedMovies.map((movie, index) => (
              <m.div
                key={movie.tmdbId}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                layout
              >
                <MovieCard 
                  movie={{
                    ...movie,
                    movieId: movie.tmdbId,
                    year: null,
                    genres: [],
                    posterUrl: movie.posterUrl ?? null,
                  }}
                  selected={true} 
                  index={index}
                  onClick={() => removeMovie(movie.tmdbId)}
                />
              </m.div>
            ))}
          </AnimatePresence>
        </LazyMotion>
      </div>
    </div>
  )
}
