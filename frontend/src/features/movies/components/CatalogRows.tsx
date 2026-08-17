import { getTrendingMovies, getNewReleases } from "@/features/movies/api"
import { MovieRow } from "./MovieRow"
import type { Movie } from "../types/movie"

export async function TrendingMoviesRow() {
  let movies: Movie[] = []
  try {
    movies = await getTrendingMovies(20)
  } catch {
    movies = []
  }
  return (
    <MovieRow
      title="Trending This Week"
      subtitle="What people are watching"
      movies={movies || []}
      category="trending"
    />
  )
}

export async function NewReleasesRow() {
  let movies: Movie[] = []
  try {
    movies = await getNewReleases(20)
  } catch {
    movies = []
  }
  return (
    <MovieRow
      title="New Releases"
      subtitle="Recently released"
      movies={movies || []}
      category="new"
    />
  )
}
