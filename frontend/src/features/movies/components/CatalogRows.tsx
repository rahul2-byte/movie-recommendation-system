import {
  getTrendingMovies,
  getPopularMovies,
  getNewReleases,
} from "@/features/movies/api"
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

export async function PopularMoviesRow() {
  let movies: Movie[] = []
  try {
    movies = await getPopularMovies(20)
  } catch {
    movies = []
  }
  return (
    <MovieRow
      title="Popular Hits"
      subtitle="Audience favourites"
      movies={movies || []}
      category="popular"
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
