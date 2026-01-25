"use client"

import { useRecommendationStore } from "@/lib/store/recommendation"
import { fetchRecommendations } from "@/lib/api/recommendations"
import { useRouter } from "next/navigation"

export function RecommendCTA({ onDone }: { onDone: () => void }) {
    const {
        selectedMovies,
        selectedGenres,
        setRecommendations,
    } = useRecommendationStore()

    const router = useRouter()

    const disabled =
        selectedMovies.length === 0 && selectedGenres.length === 0

    async function handleClick() {
        // Extract movie IDs from selected movies
        const seedMovieIds = selectedMovies.slice(0, 5).map(movie => movie.movieId)
        
        if (seedMovieIds.length === 0) {
            // If no movies selected, we can't make recommendations
            return
        }

        const requestPayload = {
            seed_movie_ids: seedMovieIds,
            moods: [], // Backend expects mood literals, not genre strings. Genres are not currently used by the API.
            limit: 99,
        }
        const data = await fetchRecommendations(requestPayload)
        console.log(data)
        setRecommendations(data.recommendations)
        onDone()
        router.push("/recommendations")
    }

    return (
        <button
            disabled={disabled}
            onClick={handleClick}
            className="w-full rounded-xl bg-gradient-to-r from-amber-400 to-rose-400 py-4 text-lg font-semibold text-black disabled:opacity-50"
        >
            Recommend Movies
        </button>
    )
}
