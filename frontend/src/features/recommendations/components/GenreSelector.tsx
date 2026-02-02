"use client"

import { useRecommendationStore } from "@/features/recommendations/store"
import { ToggleGroup, ToggleGroupItem } from "@/shared/ui/ToggleGroup"

const GENRES = [
    "Action",
    "Drama",
    "Comedy",
    "Thriller",
    "Sci-Fi",
    "Romance",
    "Horror",
    "Animation",
    "Fantasy",
    "Mystery"
]

export function GenreSelector() {
    const { selectedGenres, addGenre, removeGenre } = useRecommendationStore()

    return (
        <ToggleGroup>
            {GENRES.map((genre) => {
                const active = selectedGenres.includes(genre)
                return (
                    <ToggleGroupItem
                        key={genre}
                        active={active}
                        onClick={() =>
                            active ? removeGenre(genre) : addGenre(genre)
                        }
                    >
                        {genre}
                    </ToggleGroupItem>
                )
            })}
        </ToggleGroup>
    )
}