"use client"

import { useState, useRef, useEffect, useMemo } from "react"
import { useRecommendationStore } from "@/features/recommendations/store"
import { MAX_LIKED_MOVIES } from "@/features/recommendations/state"
import { Input } from "@/shared/ui/Input"
import { useMovieSearch } from "@/features/recommendations/hooks/useMovieSearch"
import { LazyMotion, domAnimation, m, AnimatePresence } from "framer-motion"
import { cn } from "@/shared/lib/utils"

export function MovieAutocomplete() {
  const { addMovie, selectedMovies } = useRecommendationStore()
  const { query, setQuery, results, isLoading, isError } = useMovieSearch()
  const [activeIndex, setActiveIndex] = useState(-1)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const canAddMore = selectedMovies.length < MAX_LIKED_MOVIES

  const filteredResults = useMemo(() => {
    if (!results) return []
    return results.filter(
      (movie) =>
        !selectedMovies.some((selected) => selected.movieId === movie.movieId)
    )
  }, [results, selectedMovies])

  useEffect(() => {
    setActiveIndex(-1)
  }, [filteredResults])

  useEffect(() => {
    if (activeIndex >= 0 && listRef.current) {
      const activeItem = listRef.current.children[activeIndex] as HTMLElement
      if (activeItem) {
        activeItem.scrollIntoView({ block: "nearest", behavior: "smooth" })
      }
    }
  }, [activeIndex])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!filteredResults.length) return

    if (e.key === "ArrowDown") {
      e.preventDefault()
      setActiveIndex((prev) => (prev + 1) % filteredResults.length)
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setActiveIndex(
        (prev) => (prev - 1 + filteredResults.length) % filteredResults.length
      )
    } else if (e.key === "Enter") {
      e.preventDefault()
      if (activeIndex >= 0) {
        selectMovie(filteredResults[activeIndex])
      }
    } else if (e.key === "Escape") {
      setQuery("")
    }
  }

  const selectMovie = (movie: any) => {
    addMovie({
      movieId: movie.movieId,
      title: movie.title,
      tmdbId: movie.tmdbId,
    })
    setQuery("")
    inputRef.current?.focus()
  }

  return (
    <div className="relative group">
      <Input
        ref={inputRef}
        autoFocus
        disabled={!canAddMore}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={canAddMore ? "Type to search…" : "Selection limit reached"}
        className="h-control-lg bg-surface border-border/70 focus:bg-surface-strong transition-all"
        aria-activedescendant={
          activeIndex >= 0 ? `movie-item-${activeIndex}` : undefined
        }
        aria-controls="movie-results-list"
        aria-expanded={filteredResults.length > 0}
        role="combobox"
      />

      {isLoading && (
        <div className="absolute right-4 top-4">
          <div className="animate-spin h-5 w-5 border-2 border-primary border-t-transparent rounded-pill" />
        </div>
      )}

      <LazyMotion features={domAnimation} strict>
        <AnimatePresence>
          {filteredResults.length > 0 && query.length >= 2 && (
            <m.div
              ref={listRef}
              id="movie-results-list"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              role="listbox"
              className="absolute z-50 mt-tight w-full max-h-dropdown overflow-y-auto bg-surface-strong border border-border/70 rounded-lg shadow-card no-scrollbar"
              onMouseDown={(e) => e.preventDefault()}
            >
              {filteredResults.map((movie, index) => (
                <button
                  key={movie.movieId}
                  id={`movie-item-${index}`}
                  role="option"
                  aria-selected={index === activeIndex}
                  onClick={() => selectMovie(movie)}
                  onMouseEnter={() => setActiveIndex(index)}
                  className={cn(
                    "flex w-full items-center justify-between px-card py-tight text-left transition-colors border-b border-border/40 last:border-0",
                    index === activeIndex
                      ? "bg-surface"
                      : "hover:bg-surface"
                  )}
                >
                  <div className="flex flex-col gap-1 overflow-hidden">
                    <span
                      className={cn(
                        "text-body font-semibold truncate transition-colors",
                        index === activeIndex
                          ? "text-primary"
                          : "text-foreground"
                      )}
                    >
                      {movie.title}
                    </span>
                    <div className="flex items-center gap-2 text-overline text-muted-foreground/70">
                      {movie.year && <span>{movie.year}</span>}
                      {movie.genres && movie.genres.length > 0 && (
                        <>
                          <span className="w-1 h-1 bg-border rounded-pill" />
                          <span className="truncate max-w-40">
                            {movie.genres.slice(0, 2).join(", ")}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </m.div>
          )}
        </AnimatePresence>
      </LazyMotion>

      {isError && (
        <p className="mt-tight text-overline text-destructive">
          Unable to connect to the archive.
        </p>
      )}
    </div>
  )
}
