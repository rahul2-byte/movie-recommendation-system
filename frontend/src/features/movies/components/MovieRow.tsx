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
    <section className="space-y-10">
      <div className="flex items-end justify-between px-2">
        <h2 className="text-4xl md:text-5xl font-bold tracking-tight">{title}</h2>
        <span className="text-[11px] font-bold uppercase tracking-[0.3em] text-primary mb-2 hidden md:block">
          Explore All
        </span>
      </div>
      <Carousel>
        {movies.map((movie, index) => (
          <MovieCard
            key={movie.tmdbId}
            movie={movie}
            index={index}
          />
        ))}
      </Carousel>
    </section>
  )
}
