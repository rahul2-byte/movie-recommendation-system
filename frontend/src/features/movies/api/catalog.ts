import type { Genre, Movie } from "@/features/movies/types/movie"
import { apiClient } from "@/shared/api/client"

export function getTrendingMovies(limit = 20, page = 1, refreshSeed?: number) {
  const seed = refreshSeed == null ? "" : `&refresh_seed=${refreshSeed}`
  return apiClient<Movie[]>(
    `/catalog/trending?limit=${limit}&page=${page}${seed}`,
    {
      next: { revalidate: 3600 }, // Cache trending for 1 hour
    }
  )
}

export function getPopularMovies(limit = 20, page = 1, refreshSeed?: number) {
  const seed = refreshSeed == null ? "" : `&refresh_seed=${refreshSeed}`
  return apiClient<Movie[]>(
    `/catalog/popular?limit=${limit}&page=${page}${seed}`,
    {
      next: { revalidate: 86400 }, // Cache popular for 24 hours
    }
  )
}

export function getNewReleases(limit = 20, page = 1, refreshSeed?: number) {
  const seed = refreshSeed == null ? "" : `&refresh_seed=${refreshSeed}`
  return apiClient<Movie[]>(`/catalog/new?limit=${limit}&page=${page}${seed}`, {
    next: { revalidate: 3600 },
  })
}

export function getFeaturedMovie() {
  return apiClient<Movie | null>("/catalog/featured", {
    next: { revalidate: 3600 },
  })
}

export function getGenres() {
  return apiClient<Genre[]>("/catalog/genres", {
    next: { revalidate: 86400 },
  })
}

export type DiscoverFilters = {
  genreId?: number
  yearFrom?: number
  yearTo?: number
  ratingMin?: number
  sort?: "popularity" | "rating" | "newest"
  page?: number
  limit?: number
}

export function discoverMovies(filters: DiscoverFilters = {}) {
  const params = new URLSearchParams()
  if (filters.genreId) params.set("genre_id", String(filters.genreId))
  if (filters.yearFrom) params.set("year_from", String(filters.yearFrom))
  if (filters.yearTo) params.set("year_to", String(filters.yearTo))
  if (filters.ratingMin != null) {
    params.set("rating_min", String(filters.ratingMin))
  }
  params.set("sort", filters.sort ?? "popularity")
  params.set("page", String(filters.page ?? 1))
  params.set("limit", String(filters.limit ?? 30))
  return apiClient<Movie[]>(`/catalog/discover?${params}`, {
    next: { revalidate: 3600 },
  })
}
