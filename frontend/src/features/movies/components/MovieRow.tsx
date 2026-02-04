"use client"

import { MovieCard } from "./MovieCard"
import { Carousel } from "@/shared/ui/Carousel"
import type { Movie } from "@/features/movies/types/movie"
import { MovieRowSkeleton } from "./MovieRowSkeleton"

interface MovieRowProps {
  title: string
  movies: Movie[] | null | undefined
}

export function MovieRow({ title, movies }: MovieRowProps) {
  if (movies === undefined || movies === null) {
    return <MovieRowSkeleton title={title} />
  }

  if (movies.length === 0) {
    return null
  }

  return (
    <section className="space-y-stack">
      <div className="flex items-end justify-between px-tight">
        <h2 className="text-h2 font-semibold">{title}</h2>
        <span className="hidden md:block text-overline text-muted-foreground/70">
          Explore All
        </span>
      </div>
      <Carousel>
        {movies.map((movie, index) => (
          <MovieCard key={movie.tmdbId} movie={movie} index={index} />
        ))}
      </Carousel>
    </section>
  )
}
