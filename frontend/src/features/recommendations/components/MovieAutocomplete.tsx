"use client"

import { useRef, useMemo, useState } from "react"
import { useRecommendationStore } from "@/features/recommendations/store"
import type { Movie } from "@/features/movies/types/movie"
import { Input } from "@/shared/ui/Input"
import { useMovieSearch } from "@/features/recommendations/hooks/useMovieSearch"
import Image from "next/image"
import { Search, Loader2, X } from "lucide-react"

export function MovieAutocomplete() {
  const addMovie = useRecommendationStore((state) => state.addMovie)
  const removeMovie = useRecommendationStore((state) => state.removeMovie)
  const selectedMovies = useRecommendationStore((state) => state.selectedMovies)

  const { query, setQuery, results, isLoading, isError } = useMovieSearch()
  const inputRef = useRef<HTMLInputElement>(null)
  const [activeIndex, setActiveIndex] = useState(-1)

  const canAddMore = selectedMovies.length < 5

  const filteredResults = useMemo(() => {
    if (!results) return []
    // Show top 12 results
    return results.slice(0, 12)
  }, [results])

  const toggleMovie = (movie: Movie) => {
    const tmdbId = movie.tmdbId
    const isSelected = selectedMovies.some((m) => m.tmdbId === tmdbId)
    if (isSelected) {
      removeMovie(tmdbId)
    } else if (canAddMore) {
      addMovie({
        tmdbId,
        title: movie.title,
        posterUrl: movie.posterUrl,
      })
      setQuery("")
      setActiveIndex(-1)
    }
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown" && filteredResults.length > 0) {
      event.preventDefault()
      setActiveIndex((index) => (index + 1) % filteredResults.length)
    } else if (event.key === "ArrowUp" && filteredResults.length > 0) {
      event.preventDefault()
      setActiveIndex((index) =>
        index <= 0 ? filteredResults.length - 1 : index - 1
      )
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault()
      toggleMovie(filteredResults[activeIndex])
    } else if (event.key === "Escape") {
      setQuery("")
      setActiveIndex(-1)
    }
  }

  return (
    <div className="relative">
      <label htmlFor="movie-search" className="sr-only">
        Search movies
      </label>
      <div className="relative">
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute left-4 top-3.5 z-10 h-5 w-5 text-dim"
        />
        <Input
          id="movie-search"
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search for a movie you love"
          role="combobox"
          aria-label="Search movies"
          aria-expanded={filteredResults.length > 0}
          aria-controls="movie-search-results"
          aria-activedescendant={
            activeIndex >= 0 ? `movie-result-${activeIndex}` : undefined
          }
          aria-autocomplete="list"
          autoComplete="off"
          className="h-12 border-line bg-ink pl-12 pr-12 text-paper placeholder:text-dim focus-visible:ring-crimson"
        />

        {isLoading && (
          <Loader2
            aria-label="Searching"
            className="absolute right-4 top-3.5 h-5 w-5 animate-spin text-crimson"
          />
        )}
        {!isLoading && query && (
          <button
            type="button"
            className="absolute right-2 top-2 grid size-8 place-items-center text-dim hover:text-paper"
            onClick={() => setQuery("")}
            aria-label="Clear search"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {filteredResults.length > 0 && (
        <ul
          id="movie-search-results"
          role="listbox"
          className="absolute z-30 mt-2 max-h-108 w-full overflow-y-auto border border-line bg-ink shadow-2xl"
        >
          {filteredResults.map((movie, index) => {
            const selected = selectedMovies.some(
              (item) => item.tmdbId === movie.tmdbId
            )
            return (
              <li
                id={`movie-result-${index}`}
                key={movie.tmdbId}
                role="option"
                aria-selected={selected}
              >
                <button
                  type="button"
                  className={`flex w-full items-center gap-3 p-3 text-left transition-colors ${activeIndex === index ? "bg-panel" : "hover:bg-panel/70"}`}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => toggleMovie(movie)}
                >
                  <span className="relative grid size-12 shrink-0 place-items-center overflow-hidden bg-panel text-sm font-bold text-crimson">
                    {movie.posterUrl ? (
                      <Image src={movie.posterUrl} alt="" fill sizes="48px" />
                    ) : (
                      movie.title.slice(0, 1)
                    )}
                  </span>
                  <span className="min-w-0 flex-1">
                    <strong className="block truncate text-sm text-paper">
                      {movie.title}
                    </strong>
                    <small className="block truncate text-xs text-dim">
                      {[movie.year, movie.genres[0]]
                        .filter(Boolean)
                        .join(" · ")}
                    </small>
                  </span>
                  <span className="text-xs font-bold text-crimson">
                    {selected ? "Remove" : canAddMore ? "Add" : "Full"}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {query.length >= 2 &&
        !isLoading &&
        filteredResults.length === 0 &&
        !isError && (
          <p className="mt-3 text-sm text-muted">
            We couldn&apos;t find that title. Check the spelling or try another
            movie.
          </p>
        )}
      {isError && (
        <p className="mt-3 text-sm text-danger">
          Search is unavailable. Check your connection and try again.
        </p>
      )}
    </div>
  )
}
