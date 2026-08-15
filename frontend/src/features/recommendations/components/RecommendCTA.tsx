"use client"

import { useRecommendationStore } from "@/features/recommendations/store"
import { useRecommendations } from "@/features/recommendations/hooks/useRecommendations"
import { Button } from "@/shared/ui/Button"
import { Sparkles, AlertCircle } from "lucide-react"
import { LazyMotion, domAnimation, m, AnimatePresence } from "framer-motion"

export function RecommendCTA({ onDone }: { onDone: () => void }) {
  const { selectedMovies } = useRecommendationStore()
  const { mutate, isPending, isError, error } = useRecommendations()

  const requiredCount = 5
  const selectedCount = selectedMovies.length
  const isReady = selectedCount === requiredCount

  function handleClick() {
    if (!isReady) return

    const seedTmdbIds = selectedMovies.map((movie) => movie.tmdbId)

    mutate(
      {
        seed_tmdb_ids: seedTmdbIds,
        moods: [],
        limit: 20,
      },
      {
        onSuccess: () => {
          onDone()
        },
      }
    )
  }

  return (
    <div className="space-y-stack">
      <LazyMotion features={domAnimation} strict>
        <AnimatePresence mode="wait">
          {!isReady && (
            <m.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="flex items-center gap-3 p-card bg-primary/10 border border-primary/30 rounded-lg"
            >
              <AlertCircle className="h-5 w-5 text-primary" />
              <p className="text-body text-primary">
                Select {requiredCount} movies to tune the model ({selectedCount}
                /{requiredCount}).
              </p>
            </m.div>
          )}
        </AnimatePresence>
      </LazyMotion>

      <Button
        disabled={!isReady || isPending}
        onClick={handleClick}
        size="lg"
        className="w-full rounded-lg font-semibold tracking-wide"
      >
        <div className="flex items-center justify-center gap-3">
          {isPending ? (
            <>
              <div className="animate-spin h-5 w-5 border-2 border-current border-t-transparent rounded-pill" />
              <span>Preparing your reel…</span>
            </>
          ) : (
            <>
              <Sparkles className="h-5 w-5" />
              <span>Initiate discovery</span>
            </>
          )}
        </div>
      </Button>

      {isError && (
        <div className="text-center space-y-tight">
          <p className="text-overline text-destructive">
            {error?.message?.includes("fetch") ||
            error?.message?.includes("connect")
              ? "Connection lost. Is the backend running?"
              : "We hit a snag. Please try again."}
          </p>
          {error?.message && (
            <p className="text-caption text-muted-foreground">
              {error.message}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
