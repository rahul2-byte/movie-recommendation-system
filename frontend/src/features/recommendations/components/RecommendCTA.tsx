"use client"

import { useRecommendationStore } from "@/features/recommendations/store"
import { useRecommendations } from "@/features/recommendations/hooks/useRecommendations"
import { Button } from "@/shared/ui/Button"

export function RecommendCTA({ onDone }: { onDone: () => void }) {
    const { selectedMovies, selectedGenres } = useRecommendationStore()
    const { mutate, isPending } = useRecommendations()

    const disabled =
        (selectedMovies.length === 0 && selectedGenres.length === 0) || isPending

    function handleClick() {
        const seedMovieIds = selectedMovies.slice(0, 5).map(movie => movie.movieId)
        
        if (seedMovieIds.length === 0) {
            return
        }

        mutate({
            seed_movie_ids: seedMovieIds,
            moods: [],
            limit: 99,
        }, {
            onSuccess: onDone,
        })
    }

    return (
        <Button
            disabled={disabled}
            onClick={handleClick}
            size="lg"
            className="w-full"
        >
            {isPending ? "Getting recommendations..." : "Recommend Movies"}
        </Button>
    )
}
