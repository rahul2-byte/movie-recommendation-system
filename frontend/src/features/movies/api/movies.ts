import { Movie } from "../types/movie"
import { apiClient } from "@/shared/api/client"

export async function searchMovies(
  query: string,
  page = 1,
  limit = 24
): Promise<Movie[]> {
  if (query.length < 2) return []
  return apiClient<Movie[]>(
    `/movies/search?q=${encodeURIComponent(query)}&page=${page}&limit=${limit}`
  )
}

export function getMovieDetails(tmdbId: number) {
  return apiClient<Movie>(`/movies/${tmdbId}`, {
    next: { revalidate: 3600 },
  })
}

export function getSimilarMovies(tmdbId: number, limit = 24, page = 1) {
  return apiClient<Movie[]>(
    `/movies/${tmdbId}/similar?limit=${limit}&page=${page}`,
    {
      next: { revalidate: 3600 },
    }
  )
}
