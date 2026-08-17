"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Pause,
  Play,
  Star,
} from "lucide-react"
import type { Movie } from "@/features/movies/types/movie"
import { MovieArtwork } from "./MovieArtwork"

export function Hero({
  movie,
  movies = movie ? [movie] : [],
}: {
  movie: Movie | null
  movies?: Movie[]
}) {
  const lineup = movies.length ? movies : movie ? [movie] : []
  const [activeIndex, setActiveIndex] = useState(0)
  const [paused, setPaused] = useState(false)
  const [reducedMotion, setReducedMotion] = useState(false)
  const activeMovie = lineup[activeIndex] ?? movie

  useEffect(() => {
    if (!window.matchMedia) return
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)")
    const update = () => setReducedMotion(mediaQuery.matches)
    update()
    mediaQuery.addEventListener?.("change", update)
    return () => mediaQuery.removeEventListener?.("change", update)
  }, [])

  useEffect(() => {
    if (lineup.length < 2 || paused || reducedMotion) return
    const timer = window.setInterval(() => {
      setActiveIndex((index) => (index + 1) % lineup.length)
    }, 5000)
    return () => window.clearInterval(timer)
  }, [lineup.length, paused, reducedMotion])

  const move = (direction: -1 | 1) => {
    setActiveIndex(
      (index) => (index + direction + lineup.length) % lineup.length
    )
  }

  return (
    <section
      aria-label="Featured movies"
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          setPaused(false)
        }
      }}
      className="relative isolate overflow-hidden border-b border-white/10 bg-ink text-white"
    >
      <div className="absolute inset-0">
        {activeMovie && (
          <MovieArtwork
            key={activeMovie.tmdbId}
            title={activeMovie.title}
            posterUrl={activeMovie.posterUrl}
            backdropUrl={activeMovie.backdropUrl}
            variant="backdrop"
            fallbackToPoster={false}
            highResolution
            priority
            sizes="100vw"
            alt=""
            showFallbackLabel={false}
          />
        )}
        {!activeMovie && <div className="absolute inset-0 bg-crimson" />}
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(14,14,16,0.98)_0%,rgba(14,14,16,0.84)_35%,rgba(14,14,16,0.32)_72%,rgba(14,14,16,0.5)_100%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(0deg,rgba(14,14,16,0.96)_0%,transparent_44%,rgba(14,14,16,0.2)_100%)]" />
      </div>

      <div className="relative mx-auto flex min-h-[100dvh] w-full max-w-[1600px] flex-col justify-end gap-10 px-4 pb-8 pt-28 sm:px-8 sm:pb-10 lg:px-12 lg:pb-12">
        <div className="max-w-2xl">
          <span className="text-xs font-bold uppercase tracking-[0.16em] text-white">
            Made for movie nights
          </span>
          <h1 className="mt-4 max-w-3xl text-balance font-display text-5xl leading-[0.9] tracking-[-0.055em] text-white sm:text-6xl lg:text-7xl">
            Find your next favourite film.
          </h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-white/72 sm:text-lg">
            Start with movies you love. M99 retrieves and ranks a lineup shaped
            around your taste.
          </p>
          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/#build-lineup"
              className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-crimson px-6 text-sm font-bold text-white transition-colors hover:bg-crimson-bright active:scale-[0.98]"
            >
              Build your lineup <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/catalog"
              className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson inline-flex min-h-12 items-center justify-center rounded-full border border-white/30 bg-white/10 px-6 text-sm font-bold text-white backdrop-blur transition-colors hover:bg-white/18 active:scale-[0.98]"
            >
              Explore movies
            </Link>
          </div>
        </div>

        {activeMovie && (
          <div className="flex flex-col gap-5 border-t border-white/20 pt-5 xl:flex-row xl:items-end xl:justify-between">
            <Link
              href={`/movies/${activeMovie.tmdbId}`}
              className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson min-w-0 border-l-2 border-crimson pl-4 text-sm text-white/70 transition-colors hover:text-white"
            >
              <small className="block text-xs font-bold text-crimson-bright">
                Featured this week
              </small>
              <strong className="mt-1 block truncate text-base text-white sm:text-lg">
                {activeMovie.title}
              </strong>
              <small className="mt-1 flex items-center gap-2">
                {[activeMovie.year, activeMovie.genres?.[0]]
                  .filter(Boolean)
                  .join(" / ")}
                {activeMovie.rating != null && (
                  <em className="inline-flex items-center gap-1 not-italic text-white">
                    <Star className="h-3.5 w-3.5 fill-current" />
                    {activeMovie.rating.toFixed(1)}
                  </em>
                )}
              </small>
            </Link>

            {lineup.length > 1 && (
              <div className="flex w-full items-end justify-between gap-2 xl:w-auto xl:shrink-0 xl:justify-end">
                <button
                  type="button"
                  aria-label={
                    paused
                      ? "Resume featured movie rotation"
                      : "Pause featured movie rotation"
                  }
                  aria-pressed={paused}
                  title={paused ? "Resume rotation" : "Pause rotation"}
                  onClick={() => setPaused((value) => !value)}
                  className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson grid h-10 w-10 shrink-0 place-items-center rounded-full border border-white/25 bg-black/20 text-white transition-colors hover:bg-white/15"
                >
                  {paused ? (
                    <Play className="h-4 w-4" aria-hidden="true" />
                  ) : (
                    <Pause className="h-4 w-4" aria-hidden="true" />
                  )}
                </button>
                <button
                  type="button"
                  aria-label="Previous featured movie"
                  onClick={() => move(-1)}
                  className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson grid h-10 w-10 place-items-center rounded-full border border-white/25 bg-black/20 text-white transition-colors hover:bg-white/15"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <div className="flex max-w-[min(46rem,calc(100vw-10.5rem))] snap-x gap-3 overflow-x-auto overscroll-contain [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                  {lineup.map((item, index) => (
                    <button
                      key={item.tmdbId}
                      type="button"
                      aria-label={`Show ${item.title}`}
                      onClick={() => setActiveIndex(index)}
                      className={`focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson relative h-28 w-20 shrink-0 snap-start overflow-hidden rounded-xl border transition-[transform,border-color,opacity,box-shadow] duration-300 sm:h-36 sm:w-24 lg:h-44 lg:w-28 ${index === activeIndex ? "scale-105 border-crimson-bright shadow-lg shadow-black/30" : "border-white/20 opacity-70 hover:opacity-100"}`}
                    >
                      <MovieArtwork
                        title={item.title}
                        posterUrl={item.posterUrl}
                        sizes="(max-width: 640px) 80px, (max-width: 1024px) 96px, 112px"
                        alt=""
                        showFallbackLabel={false}
                      />
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  aria-label="Next featured movie"
                  onClick={() => move(1)}
                  className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson grid h-10 w-10 place-items-center rounded-full border border-white/25 bg-black/20 text-white transition-colors hover:bg-white/15"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
