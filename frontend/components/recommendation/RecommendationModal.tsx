"use client"

import { GenreSelector } from "./GenreSelector"
import { MovieAutocomplete } from "./MovieAutocomplete"
import { SelectedMovies } from "./SelectedMovies"
import { RecommendCTA } from "./RecommendCTA"

export function RecommendationModal({
    onClose,
}: {
    onClose: () => void
}) {
    return (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm">
            <div className="mx-auto mt-20 max-w-2xl rounded-2xl bg-white p-8 shadow-xl">
                <header className="mb-6 flex items-center justify-between">
                    <h2 className="text-2xl font-semibold">
                        Tell us what you like
                    </h2>
                    <button onClick={onClose} className="text-gray-500">
                        ✕
                    </button>
                </header>
                <div className="space-y-8">
                    <GenreSelector />
                    <MovieAutocomplete />
                    <SelectedMovies />
                    <RecommendCTA onDone={onClose} />
                </div>
            </div>
        </div>
    )
}
