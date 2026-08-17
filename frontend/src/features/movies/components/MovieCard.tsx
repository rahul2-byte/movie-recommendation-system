"use client"

import type { Movie } from "@/features/movies/types/movie"
import Link from "next/link"
import { Check, Star } from "lucide-react"
import { MovieArtwork } from "./MovieArtwork"

interface MovieCardProps {
  movie: Movie
  onClick?: () => void
  selected?: boolean
  variant?: "portrait" | "landscape"
}

export function MovieCard({
  movie,
  onClick,
  selected = false,
  variant = "portrait",
}: MovieCardProps) {
  const landscape = variant === "landscape"
  const content = (
    <>
      <div
        className={`relative overflow-hidden rounded-2xl border border-line/70 bg-panel shadow-[0_10px_30px_rgba(25,25,28,0.06)] transition duration-300 group-hover:-translate-y-1 group-hover:border-muted group-hover:shadow-[0_22px_44px_rgba(25,25,28,0.14)] ${
          landscape ? "aspect-video" : "aspect-[2/3]"
        }`}
      >
        <MovieArtwork
          title={movie.title}
          posterUrl={movie.posterUrl}
          backdropUrl={movie.backdropUrl}
          variant={variant === "landscape" ? "backdrop" : "poster"}
          sizes={
            variant === "landscape"
              ? "(max-width: 640px) 82vw, (max-width: 1024px) 46vw, 30vw"
              : "(max-width: 640px) 46vw, (max-width: 1024px) 30vw, 16vw"
          }
        />
        {landscape && (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-2/3 bg-gradient-to-t from-ink via-ink/45 to-transparent" />
        )}
        {selected && (
          <div className="absolute right-3 top-3 grid size-7 place-items-center rounded-full bg-crimson text-white shadow-lg">
            <Check className="size-4" aria-label="Selected" />
          </div>
        )}
      </div>
      <div
        className={landscape ? "absolute inset-x-0 bottom-0 z-10 p-4" : "pt-3"}
      >
        <h3
          title={movie.title}
          className={`truncate text-sm font-semibold ${
            landscape ? "text-white" : "text-paper"
          }`}
        >
          {movie.title}
        </h3>
        <div
          className={`mt-1 flex items-center justify-between text-xs ${landscape ? "text-white/75" : "text-dim"}`}
        >
          <span>{movie.year ?? "Year unknown"}</span>
          {movie.rating != null && (
            <span className="inline-flex items-center gap-1 text-crimson">
              <Star aria-hidden="true" className="h-3.5 w-3.5 fill-current" />
              {movie.rating.toFixed(1)}
            </span>
          )}
        </div>
      </div>
    </>
  )

  if (onClick) {
    return (
      <button
        type="button"
        className={`focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson group relative block w-full text-left ${selected ? "rounded-2xl ring-2 ring-crimson ring-offset-3 ring-offset-canvas" : ""}`}
        onClick={onClick}
        aria-pressed={selected || undefined}
        aria-label={`${selected ? "Remove" : "Select"} ${movie.title}`}
      >
        {content}
      </button>
    )
  }

  return (
    <Link
      href={`/movies/${movie.tmdbId}`}
      className={`focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson group relative block ${selected ? "rounded-2xl ring-2 ring-crimson ring-offset-3 ring-offset-canvas" : ""}`}
      aria-label={`View details for ${movie.title}`}
    >
      {content}
    </Link>
  )
}
