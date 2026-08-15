"use client"

import { useRecommendationStore } from "@/features/recommendations/store"
import { useRecommendations } from "@/features/recommendations/hooks/useRecommendations"
import { MovieAutocomplete } from "@/features/recommendations/components/MovieAutocomplete"
import { GenreSelector } from "@/features/recommendations/components/GenreSelector"
import { SelectedMovies } from "@/features/recommendations/components/SelectedMovies"
import { Play, ArrowLeft } from "lucide-react"
import Link from "next/link"
import Image from "next/image"
import { LazyMotion, domAnimation, m } from "framer-motion"
import { Mood } from "@/features/recommendations/types"

export default function SetupPage() {
  const selectedMovies = useRecommendationStore((state) => state.selectedMovies)
  const selectedGenres = useRecommendationStore((state) => state.selectedGenres)
  const { mutate, isPending } = useRecommendations()

  const handleRecommend = () => {
    const seedTmdbIds = selectedMovies.map((m) => m.tmdbId)
    mutate({
      seed_tmdb_ids: seedTmdbIds,
      moods: selectedGenres as Mood[],
      limit: 20,
    })
  }

  const isReady = selectedMovies.length === 5

  return (
    <div className="section pt-32 min-h-screen">
      <div className="container container-narrow">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-text-muted hover:text-accent transition-colors mb-8 text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Home
        </Link>

        <LazyMotion features={domAnimation} strict>
          <m.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="heading-section mb-4">Set the Scene</h1>
            <p className="text-body mb-8 max-w-2xl">
              Select up to 5 films that resonate with you right now. We will
              analyze their DNA to find your next favorite.
            </p>

            {/* Counter Bar */}
            <div className="flex flex-col md:flex-row items-center gap-6 p-6 bg-[rgba(255,255,255,0.03)] rounded-xl mb-12 border border-[rgba(255,255,255,0.05)]">
              <div className="flex gap-2">
                {[...Array(5)].map((_, i) => {
                  const movie = selectedMovies[i]
                  return (
                    <div
                      key={i}
                      className={`w-12 h-[72px] rounded-sm border overflow-hidden flex items-center justify-center bg-[rgba(255,255,255,0.05)] ${movie ? "border-accent" : "border-[rgba(255,255,255,0.1)] border-dashed"}`}
                    >
                      {movie?.posterUrl ? (
                        <Image
                          src={movie.posterUrl}
                          alt={movie.title}
                          width={48}
                          height={72}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <span className="text-xs text-text-muted/20">
                          {i + 1}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
              <div className="flex-1 text-center md:text-left">
                <span className="text-body font-bold text-white block">
                  {selectedMovies.length}/5 Selected
                </span>
                {selectedMovies.length < 5 ? (
                  <span className="text-xs text-text-muted">
                    Select {5 - selectedMovies.length} more to unlock
                  </span>
                ) : (
                  <span className="text-xs text-accent">
                    Ready to recommend
                  </span>
                )}
              </div>

              <button
                onClick={handleRecommend}
                disabled={!isReady || isPending}
                className="btn btn-primary w-full md:w-auto"
              >
                {isPending ? (
                  "Thinking..."
                ) : (
                  <>
                    <Play className="btn-icon fill-current" />
                    Recommend
                  </>
                )}
              </button>
            </div>

            {/* Genres */}
            <div className="mb-20">
              <p className="label-accent mb-6">1. REFINE MOOD (OPTIONAL)</p>
              <GenreSelector />
            </div>

            {/* Selected Movies Grid (Persistent) */}
            <div className="mb-20">
              <SelectedMovies />
            </div>

            {/* Search */}
            <div className="mb-20">
              <p className="label-accent mb-6">2. SELECT SEEDS</p>
              <MovieAutocomplete />
            </div>
          </m.div>
        </LazyMotion>
      </div>
    </div>
  )
}
