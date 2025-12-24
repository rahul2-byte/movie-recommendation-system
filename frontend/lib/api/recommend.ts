import { apiClient } from "./client"
import { Movie } from "@/lib/types/movie"

export interface RecommendPayload {
  seed_movie_ids: number[]
  preferred_genres: string[]
  top_k: number
}

export async function fetchRecommendations(
  payload: RecommendPayload
): Promise<Movie[]> {
  const { data } = await apiClient.post<Movie[]>("/recommend", payload)
  return data
}
