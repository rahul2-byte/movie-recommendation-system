"use client"

import { useRecommendationStore } from "@/lib/store/recommendation"

export function SelectedMovies() {
    const { selectedMovies, removeMovie } =
        useRecommendationStore()

    if (selectedMovies.length === 0) return null

    return (
        <section>
            <h3 className="mb-2 text-sm text-gray-600">
                Selected movies ({selectedMovies.length} / 5)
            </h3>
            <div className="flex flex-wrap gap-2">
                {selectedMovies.map((m) => (
                    <span
                        key={m.movieId}
                        className="flex items-center gap-2 rounded-full bg-gray-100 px-3 py-1"
                    >
                        <span className="text-sm font-medium">{m.title}</span>
                        <button
                            onClick={() => removeMovie(m.movieId)}
                            className="text-gray-500 hover:text-black"
                        >
                            ✕
                        </button>
                    </span>
                ))}
            </div>
        </section>
    )
}
