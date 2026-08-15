import type { Movie } from "@/features/movies/types/movie"
import { apiClient } from "@/shared/api/client"

export function getTrendingMovies(limit = 20) {
  return apiClient<Movie[]>(`/catalog/trending?limit=${limit}`, {
    next: { revalidate: 3600 }, // Cache trending for 1 hour
  })
}

export function getPopularMovies(limit = 20) {
  return apiClient<Movie[]>(`/catalog/popular?limit=${limit}`, {
    next: { revalidate: 86400 }, // Cache popular for 24 hours
  })
}

export function getNewReleases(limit = 20) {
  return apiClient<Movie[]>(`/catalog/new?limit=${limit}`, {
    next: { revalidate: 3600 },
  })
}
