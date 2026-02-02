"use client"

import { useRecommendationStore } from "@/features/recommendations/store"
import { MAX_LIKED_MOVIES } from '@/features/recommendations/state'
import { Input } from "@/shared/ui/Input"
import { useMovieSearch } from "@/features/recommendations/hooks/useMovieSearch"

export function MovieAutocomplete() {
    const { addMovie, selectedMovies } = useRecommendationStore()
    const { query, setQuery, results, isLoading, isError } = useMovieSearch()

    const disabled = selectedMovies.length >= MAX_LIKED_MOVIES

    return (
        <div className="relative">
            <Input
                disabled={disabled}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search movies you love…"
            />

            {isLoading && <p>Loading...</p>}
            {isError && <p>Error searching for movies.</p>}

            {results && results.length > 0 && (
                <div className="absolute z-20 mt-2 w-full rounded-2xl bg-card border border-border/50 shadow-2xl overflow-hidden backdrop-blur-xl">
                    {results.map((movie) => (
                        <button
                            key={movie.movieId}
                            onClick={() => {
                                addMovie({
                                    movieId: movie.movieId,
                                    title: movie.title,
                                    tmdbId: movie.tmdbId,
                                })
                                setQuery("")
                            }}
                            className="flex w-full items-center gap-3 px-6 py-4 text-left hover:bg-black/5 transition-colors border-b border-border/20 last:border-0"
                        >
                            <span className="font-semibold text-foreground">
                                {movie.title}
                            </span>
                        </button>
                    ))}
                </div>
            )}
        </div>
    )
}
