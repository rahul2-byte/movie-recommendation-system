import { RecommendRequest, RecommendResponse } from "../types"
import { apiClient } from "@/shared/api/client"

export async function fetchRecommendations(
  payload: RecommendRequest
): Promise<RecommendResponse> {
  return apiClient<RecommendResponse>("/recommend", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function fetchRecommendationPage(sessionId: string, offset: number) {
  return apiClient<RecommendResponse>(
    `/recommend/${encodeURIComponent(sessionId)}?offset=${offset}`
  )
}
