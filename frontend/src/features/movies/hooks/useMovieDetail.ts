import { useQuery } from "@tanstack/react-query"
import { Movie } from "../types/movie"
import { getMovieDetails } from "../api/movies"

export async function fetchMovieDetail(
  movieId: number | null,
  tmdbId?: number | null
): Promise<Movie | null> {
  const id = movieId && movieId > 0 ? movieId : tmdbId
  if (!id) return null
  try {
    return await getMovieDetails(id)
  } catch (error) {
    console.error(
      `Error fetching movie details. tmdbId: ${id}, error: ${error}`
    )
    return null
  }
}

export function useMovieDetail(movieId: number | null, tmdbId?: number | null) {
  return useQuery<Movie | null, Error>({
    queryKey: ["movieDetail", movieId, tmdbId],
    queryFn: () => fetchMovieDetail(movieId, tmdbId),
    enabled:
      (movieId !== null && movieId > 0) ||
      (tmdbId !== null && tmdbId !== undefined),
    staleTime: 1000 * 60 * 60, // 1 hour
    gcTime: 1000 * 60 * 60 * 24, // 24 hours
  })
}
