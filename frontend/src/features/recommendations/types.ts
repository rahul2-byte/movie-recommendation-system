export interface RecommendRequest {
  seed_tmdb_ids: number[]
  limit?: number
  refresh_seed?: number
}

export interface RecommendedMovie {
  tmdbId: number
  title: string
  year?: number
  posterUrl?: string
  rating?: number
  genres: string[]
  rankScore?: number
  overview?: string
}

export interface RecommendResponse {
  recommendations: RecommendedMovie[]
  sessionId: string
  nextOffset: number | null
  hasMore: boolean
}
