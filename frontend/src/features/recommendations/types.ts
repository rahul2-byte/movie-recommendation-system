export type Mood =
  | "FEEL_GOOD"
  | "DARK"
  | "INSPIRING"
  | "FOCUS"
  | "ADVENTURE"
  | "CHILL"

export interface RecommendRequest {
  seed_tmdb_ids: number[]
  moods?: Mood[]
  limit?: number
}

export interface RecommendedMovie {
  tmdbId: number
  title: string
  year?: number
  posterUrl?: string
  rating?: number
  genres: string[]
  score: number
  overview?: string
}

export interface RecommendResponse {
  recommendations: RecommendedMovie[]
}
