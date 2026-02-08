"use client"

import { useState, useRef, useMemo } from "react"
import { useRecommendationStore } from "@/features/recommendations/store"
import { MAX_LIKED_MOVIES } from "@/features/recommendations/state"
import { Input } from "@/shared/ui/Input"
import { useMovieSearch } from "@/features/recommendations/hooks/useMovieSearch"
import { LazyMotion, domAnimation, m, AnimatePresence } from "framer-motion"
import { MovieCard } from "@/features/movies/components/MovieCard"
import { Search, Loader2 } from "lucide-react"

export function MovieAutocomplete() {
  const { addMovie, removeMovie, selectedMovies } = useRecommendationStore()
  const { query, setQuery, results, isLoading, isError } = useMovieSearch()
  const inputRef = useRef<HTMLInputElement>(null)

  const canAddMore = selectedMovies.length < MAX_LIKED_MOVIES

  const filteredResults = useMemo(() => {
    if (!results) return []
    // Show top 12 results
    return results.slice(0, 12)
  }, [results])

  const toggleMovie = (movie: any) => {
    // Backend returns movieId (or movie_id). 
    // We should be consistent. Our store uses movieId.
    const mid = movie.movieId || movie.movie_id
    const isSelected = selectedMovies.some((m) => m.movieId === mid)
    if (isSelected) {
      removeMovie(mid)
    } else if (canAddMore) {
      addMovie({
        movieId: mid,
        title: movie.title,
        tmdbId: movie.tmdbId,
        posterUrl: movie.posterUrl,
      })
    }
  }

  return (
    <div className="space-y-12">
      <div className="relative max-w-2xl mx-auto">
        <Search className="absolute left-6 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
        <Input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for movies to add to your seeds..."
          className="h-[64px] bg-[rgba(255,255,255,0.05)] border-[rgba(255,255,255,0.1)] focus:border-accent focus:bg-[rgba(255,255,255,0.08)] transition-all rounded-full pl-14 pr-6 text-lg text-white placeholder:text-gray-500"
        />

        {isLoading && (
          <div className="absolute right-6 top-1/2 -translate-y-1/2">
            <Loader2 className="animate-spin h-5 w-5 text-accent" />
          </div>
        )}
      </div>

      <div className="min-h-[400px]">
        <LazyMotion features={domAnimation} strict>
          <AnimatePresence mode="wait">
            {filteredResults.length > 0 ? (
              <m.div
                key="results"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-6"
              >
                {filteredResults.map((movie, index) => {
                  const mid = movie.movieId || movie.movie_id
                  const isSelected = selectedMovies.some((m) => m.movieId === mid)
                  return (
                    <MovieCard
                      key={mid}
                      movie={{...movie, movieId: mid}}
                      index={index}
                      selected={isSelected}
                      onClick={() => toggleMovie(movie)}
                    />
                  )
                })}
              </m.div>
            ) : query.length >= 2 && !isLoading ? (
              <m.div
                key="no-results"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center py-20 text-text-muted"
              >
                <Search className="w-12 h-12 mb-4 opacity-20" />
                <p className="text-xl">No movies found matching "{query}"</p>
                <p className="text-sm">Try searching for something else.</p>
              </m.div>
            ) : null}
          </AnimatePresence>
        </LazyMotion>

        {isError && (
          <div className="text-center py-20">
            <p className="text-error text-xl mb-2">Unable to connect to the archive.</p>
            <p className="text-text-muted">Please check your connection and try again.</p>
          </div>
        )}
      </div>
    </div>
  )
}
