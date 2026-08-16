import { Movie } from "@/features/movies/types/movie"
import { MovieCard } from "./MovieCard"

export function CatalogGrid({ movies }: { movies: Movie[] }) {
  return (
    <div className="grid grid-cols-2 gap-x-3 gap-y-8 sm:grid-cols-3 sm:gap-x-4 lg:grid-cols-5 xl:grid-cols-6">
      {movies
        .filter((movie) => movie.posterUrl)
        .map((movie) => (
          <MovieCard key={movie.tmdbId} movie={movie} />
        ))}
    </div>
  )
}
