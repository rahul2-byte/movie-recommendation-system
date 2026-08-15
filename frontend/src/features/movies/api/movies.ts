import { Movie } from "../types/movie"
import { apiClient } from "@/shared/api/client"

export async function searchMovies(query: string): Promise<Movie[]> {
  if (query.length < 2) return []

  try {
    return await apiClient<Movie[]>(`/movies/search?q=${query}`)
  } catch {
    return []
  }
}
