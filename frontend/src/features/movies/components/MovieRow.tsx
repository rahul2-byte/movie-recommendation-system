"use client"

import { MovieCard } from "./MovieCard"
import { Carousel } from "@/shared/ui/Carousel"
import type { Movie } from "@/features/movies/types/movie"
import { MovieRowSkeleton } from "./MovieRowSkeleton"
import { MovieDetailModal } from "./MovieDetailModal"
import { useState } from "react"

interface MovieRowProps {
  title: string
  movies: Movie[] | null | undefined
}

export function MovieRow({ title, movies }: MovieRowProps) {
  const [selectedMovieId, setSelectedMovieId] = useState<number | null>(null)
  const [selectedTmdbId, setSelectedTmdbId] = useState<number | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const handleMovieClick = (movieId: number, tmdbId: number) => {
    setSelectedMovieId(movieId)
    setSelectedTmdbId(tmdbId)
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedMovieId(null)
    setSelectedTmdbId(null)
  }

  if (movies === undefined || movies === null) {
    return <MovieRowSkeleton title={title} />
  }

  if (movies.length === 0) {
    return null
  }

  return (
    <>
      <section className="space-y-stack">
        <div className="flex items-end justify-between px-tight">
          <h2 className="text-h2 font-semibold">{title}</h2>
          <span className="hidden md:block text-overline text-muted-foreground/70">
            Explore All
          </span>
        </div>
        <Carousel>
          {movies.map((movie, index) => (
            <div 
              key={movie.tmdbId} 
              className="flex-none w-[180px] md:w-[220px] lg:w-[260px] aspect-[2/3]"
            >
              <MovieCard 
                movie={movie} 
                index={index} 
                onClick={() => handleMovieClick(movie.movieId, movie.tmdbId)} 
              />
            </div>
          ))}
        </Carousel>
      </section>
      <MovieDetailModal
        movieId={selectedMovieId}
        tmdbId={selectedTmdbId}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
      />
    </>
  )
}
