"use client"

import { useRecommendationStore } from "@/lib/store/recommendation"

const GENRES = [
    "Action",
    "Drama",
    "Comedy",
    "Thriller",
    "Sci-Fi",
    "Romance",
    "Horror",
]

export function GenreSelector() {
    const { selectedGenres, addGenre, removeGenre } =
        useRecommendationStore()

    return (
        <section>
            <h3 className="mb-3 text-sm font-medium text-gray-600">
                Pick genres (optional)
            </h3>
            <div className="flex flex-wrap gap-2">
                {GENRES.map((genre) => {
                    const active = selectedGenres.includes(genre)
                    return (
                        <button
                            key={genre}
                            onClick={() =>
                                active ? removeGenre(genre) : addGenre(genre)
                            }
                            className={`rounded-full px-4 py-2 text-sm transition ${active
                                    ? "bg-black text-white"
                                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                                }`}
                        >
                            {genre}
                        </button>
                    )
                })}
            </div>
        </section>
    )
}
