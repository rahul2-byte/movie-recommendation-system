"use client"

import Image from "next/image"
import { Trash2, X } from "lucide-react"
import { useRecommendationStore } from "@/features/recommendations/store"

export function SelectedMovies() {
  const { selectedMovies, removeMovie, clearMovies } = useRecommendationStore()

  return (
    <div className="mt-5 rounded-2xl border border-line bg-canvas/60 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <strong className="block text-sm text-paper">Your film strip</strong>
          <span className="text-xs text-dim">
            {selectedMovies.length}/5 selected
          </span>
        </div>
        {selectedMovies.length > 0 && (
          <button
            type="button"
            onClick={clearMovies}
            className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson inline-flex items-center gap-1.5 text-xs font-bold text-muted hover:text-paper"
          >
            <Trash2 className="h-4 w-4" /> Clear
          </button>
        )}
      </div>

      <div className="mt-4 grid grid-cols-5 gap-2" aria-label="Selected movies">
        {[...Array(5)].map((_, index) => {
          const movie = selectedMovies[index]
          return (
            <div
              className={`relative aspect-[2/3] overflow-hidden rounded-xl border ${movie ? "border-line bg-panel" : "border-dashed border-line bg-panel/60"}`}
              key={index}
            >
              {movie ? (
                <>
                  {movie.posterUrl ? (
                    <Image
                      src={movie.posterUrl}
                      alt=""
                      fill
                      sizes="112px"
                      className="object-cover"
                    />
                  ) : (
                    <span className="grid h-full place-items-center text-lg font-bold text-crimson">
                      {movie.title.slice(0, 1)}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => removeMovie(movie.tmdbId)}
                    aria-label={`Remove ${movie.title}`}
                    className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson absolute right-1.5 top-1.5 grid size-7 place-items-center rounded-full bg-ink/85 text-white transition-colors hover:bg-crimson"
                  >
                    <X className="h-4 w-4" />
                  </button>
                  <span className="sr-only">{movie.title}</span>
                </>
              ) : (
                <span className="grid h-full place-items-center text-sm font-bold text-dim">
                  {index + 1}
                </span>
              )}
            </div>
          )
        })}
      </div>
      <p className="mt-3 text-xs leading-5 text-dim">
        {selectedMovies.length === 0
          ? "Select at least one movie. You can add up to five."
          : selectedMovies.length < 5
            ? "Your lineup is ready. Add another title if you want to refine it."
            : "Five titles selected. Your film strip is ready."}
      </p>
    </div>
  )
}
