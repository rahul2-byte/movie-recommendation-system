"use client"

import { useRecommendationStore } from "@/features/recommendations/store"
import { LazyMotion, domAnimation, m, AnimatePresence } from "framer-motion"
import { X } from "lucide-react"

export function SelectedMovies() {
  const { selectedMovies, removeMovie } = useRecommendationStore()

  if (selectedMovies.length === 0) return null

  return (
    <div className="flex flex-wrap gap-3 mt-tight">
      <LazyMotion features={domAnimation} strict>
        <AnimatePresence>
          {selectedMovies.map((movie) => (
            <m.div
              key={movie.movieId}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex items-center gap-2 px-chip py-tight bg-surface border border-border rounded-pill"
            >
              <span className="text-overline text-foreground truncate max-w-48">
                {movie.title}
              </span>
              <button
                onClick={() => removeMovie(movie.movieId)}
                className="text-muted-foreground hover:text-primary transition-colors"
              >
                <X className="h-3 w-3" />
              </button>
            </m.div>
          ))}
        </AnimatePresence>
      </LazyMotion>
    </div>
  )
}
