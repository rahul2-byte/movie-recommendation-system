"use client"

import { Movie } from "@/features/movies/types/movie"
import { MovieCard } from "./MovieCard"
import { useState } from "react"
import dynamic from "next/dynamic"

const MovieDetailModal = dynamic(
  () => import("./MovieDetailModal").then((mod) => mod.MovieDetailModal),
  {
    ssr: false,
  }
)

export function CatalogGrid({ movies }: { movies: Movie[] }) {
  const [selectedMovieId, setSelectedMovieId] = useState<number | null>(null)
  const [selectedTmdbId, setSelectedTmdbId] = useState<number | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const handleMovieClick = (movieId: number, tmdbId: number) => {
    setSelectedMovieId(movieId)
    setSelectedTmdbId(tmdbId)
    setIsModalOpen(true)
  }

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {movies.map((movie, index) => (
          <MovieCard
            key={`${movie.movieId}-${index}`}
            movie={movie}
            index={index}
            onClick={() => handleMovieClick(movie.movieId, movie.tmdbId)}
          />
        ))}
      </div>
      <MovieDetailModal
        movieId={selectedMovieId}
        tmdbId={selectedTmdbId}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </>
  )
}
