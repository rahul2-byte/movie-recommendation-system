"use client"

import { useEffect, useState } from "react"
import { searchMovies } from "@/lib/api/movies"
import { useRecommendationStore } from "@/lib/store/recommendation"
import { MAX_LIKED_MOVIES } from '@/features/recommendations/state'

export function MovieAutocomplete() {
    const [query, setQuery] = useState("")
    const [results, setResults] = useState<any[]>([])
    const { addMovie, selectedMovies } = useRecommendationStore()

    useEffect(() => {
        if (query.length < 2) {
            setResults([])
            return
        }

        const id = setTimeout(async () => {
            const res = await searchMovies(query)
            setResults(res)
        }, 300)

        return () => clearTimeout(id)
    }, [query])

    const disabled = selectedMovies.length >= MAX_LIKED_MOVIES

    return (
        <div className="relative">
            <input
                disabled={disabled}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search movies you love…"
                className="w-full rounded-lg border px-4 py-3"
            />

            {results.length > 0 && (
                <div className="absolute z-20 mt-2 w-full rounded-lg bg-white shadow-lg">
                    {results.map((movie) => (
                        <button
                            key={movie.movie_id}
                            onClick={() => {
                                addMovie({
                                    movieId: movie.movie_id,
                                    title: movie.title,
                                    tmdbId: movie.tmdb_id,
                                })
                                setQuery("")
                                setResults([])
                            }}
                            className="flex w-full items-center gap-3 px-4 py-2 hover:bg-gray-100"
                        >
                            <span className="font-medium">
                                {movie.title}
                            </span>
                        </button>
                    ))}
                </div>
            )}
        </div>
    )
}
