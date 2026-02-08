"use client"

import { useRecommendationStore } from "@/features/recommendations/store"
import { ToggleGroup, ToggleGroupItem } from "@/shared/ui/ToggleGroup"
import { Mood } from "../types"

const MOODS: { label: string; value: Mood }[] = [
    { label: "Dark", value: "DARK" },
    { label: "Feel-good", value: "FEEL_GOOD" },
    { label: "Romantic", value: "ROMANTIC" },
    { label: "Thrilling", value: "THRILLING" },
    { label: "Chill", value: "CHILL" },
    { label: "Adventurous", value: "ADVENTUROUS" },
]

export function GenreSelector() {
    const { selectedGenres, addGenre, removeGenre } = useRecommendationStore()

    return (
        <ToggleGroup>
            {MOODS.map((mood) => {
                const active = selectedGenres.includes(mood.value)
                return (
                    <ToggleGroupItem
                        key={mood.value}
                        active={active}
                        onClick={() =>
                            active ? removeGenre(mood.value) : addGenre(mood.value)
                        }
                    >
                        {mood.label}
                    </ToggleGroupItem>
                )
            })}
        </ToggleGroup>
    )
}