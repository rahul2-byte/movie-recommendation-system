import {
  getTrendingMovies,
  getPopularMovies,
  getNewReleases,
} from "@/features/movies/api"
import { MovieRow } from "./MovieRow"

export async function TrendingMoviesRow() {
  const movies = await getTrendingMovies(20)
  return (
    <MovieRow
      title="Trending This Week"
      subtitle="Curated by our algorithms"
      movies={movies || []}
      category="trending"
    />
  )
}

export async function PopularMoviesRow() {
  const movies = await getPopularMovies(20)
  return (
    <MovieRow
      title="Popular Hits"
      subtitle="Most watched globally"
      movies={movies || []}
      category="popular"
    />
  )
}

export async function NewReleasesRow() {
  const movies = await getNewReleases(20)
  return (
    <MovieRow
      title="New Releases"
      subtitle="Fresh from the cinema"
      movies={movies || []}
      category="new"
    />
  )
}
