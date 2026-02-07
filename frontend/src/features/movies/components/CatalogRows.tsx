import { getTrendingMovies, getPopularMovies, getNewReleases } from "@/features/movies/api"
import { MovieRow } from "./MovieRow"

export async function TrendingMoviesRow() {
  const movies = await getTrendingMovies(20)
  return <MovieRow title="Trending now" movies={movies || []} />
}

export async function PopularMoviesRow() {
  const movies = await getPopularMovies(20)
  return <MovieRow title="Popular hits" movies={movies || []} />
}

export async function NewReleasesRow() {
  const movies = await getNewReleases(20)
  return <MovieRow title="Fresh arrivals" movies={movies || []} />
}
