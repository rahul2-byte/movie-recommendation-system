export type Mood =
  | "FEEL_GOOD"
  | "DARK"
  | "ROMANTIC"
  | "ADVENTUROUS"
  | "THRILLING"
  | "CHILL"

export interface RecommendRequest {
  seed_movie_ids: number[]
  moods?: Mood[]
  limit?: number
}

export interface RecommendedMovie {
  movieId: number
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
