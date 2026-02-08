"use client"

import { MovieCard } from "./MovieCard"
import { Carousel } from "@/shared/ui/Carousel"
import type { Movie } from "@/features/movies/types/movie"
import { MovieRowSkeleton } from "./MovieRowSkeleton"
import { MovieDetailModal } from "./MovieDetailModal"
import { useState } from "react"
import Link from "next/link"

interface MovieRowProps {
  title: string
  subtitle?: string
  movies: Movie[] | null | undefined
  category?: string
}

export function MovieRow({ title, subtitle = "Curated by our algorithms", movies, category = "trending" }: MovieRowProps) {
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
      <section className="section">
        <div className="container">
          <div className="flex flex-col md:flex-row justify-between items-end mb-12 gap-4">
            <div className="flex flex-col gap-2">
              <span className="label-accent">{subtitle}</span>
              <h2 className="heading-section">{title}</h2>
            </div>
            
            <Link href={`/catalog?category=${category}`} className="text-sm font-medium uppercase tracking-wider text-accent flex items-center gap-1 hover:gap-2 transition-all">
              View All <span>→</span>
            </Link>
          </div>

          <Carousel>
            {movies.map((movie, index) => (
              <div 
                key={movie.tmdbId} 
                className="flex-none w-[calc(50%-1rem)] md:w-[calc(33.33%-1.33rem)] lg:w-[calc(25%-1.5rem)] aspect-[2/3]"
              >
                <MovieCard 
                  movie={movie} 
                  index={index} 
                  onClick={() => handleMovieClick(movie.movieId, movie.tmdbId)} 
                />
              </div>
            ))}
          </Carousel>
        </div>
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
