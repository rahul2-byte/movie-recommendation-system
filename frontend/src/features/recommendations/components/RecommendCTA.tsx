"use client"

import { useRecommendationStore } from "@/features/recommendations/store"
import { useRecommendations } from "@/features/recommendations/hooks/useRecommendations"
import { Button } from "@/shared/ui/Button"
import { ArrowRight, AlertCircle } from "lucide-react"

export function RecommendCTA({ onDone }: { onDone: () => void }) {
  const { selectedMovies } = useRecommendationStore()
  const { mutate, isPending, isError, error } = useRecommendations()

  const selectedCount = selectedMovies.length
  const isReady = selectedCount >= 1

  function handleClick() {
    if (!isReady) return

    const seedTmdbIds = selectedMovies.map((movie) => movie.tmdbId)

    mutate(
      {
        seed_tmdb_ids: seedTmdbIds,
        limit: 200,
      },
      {
        onSuccess: () => {
          onDone()
        },
      }
    )
  }

  return (
    <div className="mt-5">
      {!isReady && (
        <div
          className="mb-4 flex items-center gap-2 border-l-2 border-crimson bg-crimson/10 p-3 text-sm text-muted"
          role="status"
        >
          <AlertCircle className="h-5 w-5" />
          <p>Select at least one movie to create a lineup.</p>
        </div>
      )}

      <Button
        disabled={!isReady || isPending}
        onClick={handleClick}
        size="lg"
        className="w-full"
      >
        <div className="flex items-center justify-center gap-3">
          {isPending ? (
            <>
              <span
                className="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
                aria-hidden="true"
              />
              <span>Finding your next watch…</span>
            </>
          ) : (
            <>
              <span>Create my lineup</span>
              <ArrowRight className="h-5 w-5" />
            </>
          )}
        </div>
      </Button>

      {isError && (
        <div
          className="mt-4 border-l-2 border-danger bg-danger/10 p-3 text-sm text-danger"
          role="alert"
        >
          <p className="font-semibold">
            {error?.message?.includes("fetch") ||
            error?.message?.includes("connect")
              ? "Connection lost. Is the backend running?"
              : "We hit a snag. Please try again."}
          </p>
          {error?.message && (
            <small className="mt-1 block text-danger/75">{error.message}</small>
          )}
        </div>
      )}
    </div>
  )
}
