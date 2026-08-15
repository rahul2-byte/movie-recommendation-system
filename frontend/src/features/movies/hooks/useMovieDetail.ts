import { useQuery } from "@tanstack/react-query"
import { Movie } from "../types/movie"
import { env } from "@/shared/config/env"

const API_BASE = env.NEXT_PUBLIC_API_BASE

export async function fetchMovieDetail(
  movieId: number | null,
  tmdbId?: number | null
): Promise<Movie | null> {
  let url = ""
  if (movieId && movieId > 0) {
    url = `${API_BASE}/api/v1/movies/${movieId}`
  } else if (tmdbId) {
    url = `${API_BASE}/api/v1/movies/tmdb/${tmdbId}`
  } else {
    return null
  }

  try {
    const res = await fetch(url)
    if (!res.ok) {
      console.error(
        `Failed to fetch movie details. url: ${url}, status: ${res.status}`
      )
      return null
    }
    return res.json()
  } catch (error) {
    console.error(`Error fetching movie details. url: ${url}, error: ${error}`)
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
