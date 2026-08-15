"use client"

import { Modal } from "@/shared/ui/Modal"
import Image from "next/image"
import { Star, Info, X, RotateCcw } from "lucide-react"
import { useMovieDetail } from "../hooks/useMovieDetail"
import { formatMovieTitle } from "@/shared/lib/utils"

export function MovieDetailModal({
  movieId,
  tmdbId,
  isOpen,
  onClose,
}: {
  movieId: number | null
  tmdbId?: number | null
  isOpen: boolean
  onClose: () => void
}) {
  const {
    data: movie,
    isLoading,
    isError,
    refetch,
  } = useMovieDetail(movieId, tmdbId)

  if (!isOpen) return null

  // Loading State
  if (isLoading) {
    return (
      <Modal>
        <div className="h-[400px] w-full bg-[rgba(255,255,255,0.05)] animate-pulse relative">
          <button
            className="absolute top-6 right-6 z-50 p-2 rounded-full bg-black/50 text-white"
            onClick={onClose}
          >
            <X className="h-6 w-6" />
          </button>
        </div>
        <div className="p-8 space-y-4">
          <div className="h-8 bg-[rgba(255,255,255,0.05)] rounded w-1/3 animate-pulse" />
          <div className="h-4 bg-[rgba(255,255,255,0.05)] rounded w-full animate-pulse" />
          <div className="h-4 bg-[rgba(255,255,255,0.05)] rounded w-2/3 animate-pulse" />
        </div>
      </Modal>
    )
  }

  // Error State
  if (isError || !movie) {
    return (
      <Modal>
        <div className="h-[300px] flex flex-col items-center justify-center gap-4 text-center p-8">
          <p className="text-xl text-error">Failed to load movie details.</p>
          <button onClick={() => refetch()} className="btn btn-secondary">
            <RotateCcw className="w-4 h-4" />
            Try Again
          </button>
          <button
            className="absolute top-6 right-6 p-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors"
            onClick={onClose}
          >
            <X className="h-6 w-6" />
          </button>
        </div>
      </Modal>
    )
  }

  const formattedTitle = formatMovieTitle(movie.title)

  return (
    <Modal>
      {/* HEADER */}
      <div className="relative h-[400px] w-full bg-black">
        {/* Image */}
        {movie.backdropUrl || movie.posterUrl ? (
          <Image
            src={movie.backdropUrl || movie.posterUrl || ""}
            alt={formattedTitle}
            fill
            className="object-cover object-top opacity-80"
            priority
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center bg-zinc-900">
            <span className="text-text-muted font-serif italic">
              No preview available
            </span>
          </div>
        )}

        {/* Gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-black/20 to-[#0a0a0a]" />

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-6 right-6 w-10 h-10 bg-black/50 hover:bg-black/80 backdrop-blur-md rounded-full text-white flex items-center justify-center transition-all z-20"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Title & Meta */}
        <div className="absolute bottom-0 left-0 w-full p-8 z-10">
          <h2 className="font-serif text-4xl md:text-5xl text-white mb-3 leading-tight">
            {formattedTitle}
          </h2>

          <div className="flex items-center gap-4 text-base text-text-secondary">
            <span className="text-white">{movie.year}</span>
            <span>•</span>
            {movie.runtime && <span>{movie.runtime} min</span>}
            <span>•</span>
            {movie.voteAverage && (
              <span className="flex items-center gap-1 text-accent">
                <Star className="w-4 h-4 fill-current" />{" "}
                {movie.voteAverage.toFixed(1)}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* BODY */}
      <div className="p-8 bg-[#0a0a0a]">
        {/* Match Score / Explanation */}
        {movie.score && (
          <div className="mb-8 p-4 bg-accent/10 border border-accent/20 rounded-lg flex items-start gap-3">
            <Info className="w-5 h-5 text-accent shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-accent font-bold mb-1">
                {Math.round(movie.score * 100)}% Match
              </p>
              {movie.retrieval_sources && (
                <p className="text-xs text-text-muted">
                  Recommended because:{" "}
                  {movie.retrieval_sources
                    .map((s) => s.replace(/_/g, " "))
                    .join(", ")}
                </p>
              )}
            </div>
          </div>
        )}

        <div className="space-y-8">
          {/* Synopsis */}
          <div>
            <h3 className="font-serif text-xl text-white mb-4">Synopsis</h3>
            <p className="text-body leading-relaxed">
              {movie.overview || "No synopsis available."}
            </p>
          </div>

          {/* Genres */}
          <div>
            <h3 className="font-serif text-xl text-white mb-4">Genres</h3>
            <div className="flex flex-wrap gap-2">
              {movie.genres.map((g) => (
                <span
                  key={g}
                  className="px-4 py-2 bg-white/5 border border-white/10 rounded-full text-sm text-text-secondary hover:bg-white/10 transition-colors cursor-default"
                >
                  {g}
                </span>
              ))}
            </div>
          </div>

          {/* Cast & Crew */}
          <div className="grid md:grid-cols-2 gap-8">
            {movie.cast && movie.cast.length > 0 && (
              <div>
                <h3 className="font-serif text-xl text-white mb-4">Cast</h3>
                <p className="text-body text-text-secondary">
                  {movie.cast.slice(0, 5).join(", ")}
                </p>
              </div>
            )}
            {movie.director && (
              <div>
                <h3 className="font-serif text-xl text-white mb-4">Director</h3>
                <p className="text-body text-text-secondary">
                  {movie.director}
                </p>
              </div>
            )}
          </div>

          {/* Tagline */}
          {movie.tagline && (
            <div>
              <h3 className="font-serif text-xl text-white mb-4">Tagline</h3>
              <p className="text-lg italic text-text-muted">
                &ldquo;{movie.tagline}&rdquo;
              </p>
            </div>
          )}
        </div>
      </div>
    </Modal>
  )
}
