"use client"

import { MovieCard } from "./MovieCard"
import { Carousel } from "@/shared/ui/Carousel"
import type { Movie } from "@/features/movies/types/movie"
import { MovieRowSkeleton } from "./MovieRowSkeleton"
import Link from "next/link"

interface MovieRowProps {
  title: string
  subtitle?: string
  movies: Movie[] | null | undefined
  category?: string
  showViewAll?: boolean
  variant?: "portrait" | "landscape"
}

export function MovieRow({
  title,
  subtitle = "Curated by our algorithms",
  movies,
  category = "trending",
  showViewAll = true,
  variant = "portrait",
}: MovieRowProps) {
  if (movies === undefined || movies === null) {
    return <MovieRowSkeleton title={title} />
  }

  if (movies.length === 0) {
    return null
  }

  return (
    <section className="py-12 first:pt-16 sm:py-16">
      <div className="mx-auto w-full max-w-[1440px] px-4 sm:px-6 lg:px-10">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <span className="text-xs font-bold uppercase tracking-[0.16em] text-crimson">
              {subtitle}
            </span>
            <h2 className="mt-2 font-display text-3xl leading-none tracking-[-0.035em] text-paper sm:text-4xl">
              {title}
            </h2>
          </div>

          {showViewAll && (
            <Link
              href={`/catalog?category=${category}`}
              className="shrink-0 text-sm font-bold text-crimson transition-colors hover:text-paper"
            >
              View all <span aria-hidden="true">→</span>
            </Link>
          )}
        </div>

        <Carousel>
          {movies
            .filter((movie) => movie.posterUrl)
            .map((movie) => (
              <div
                key={movie.tmdbId}
                className={`shrink-0 ${
                  variant === "portrait"
                    ? "w-[42vw] max-w-[190px] sm:w-[180px] lg:w-[190px]"
                    : "w-[78vw] sm:w-[400px]"
                }`}
              >
                <MovieCard movie={movie} variant={variant} />
              </div>
            ))}
        </Carousel>
      </div>
    </section>
  )
}
