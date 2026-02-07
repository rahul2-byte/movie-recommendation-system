import { RecommendRequest, RecommendResponse } from "../types"
import { env } from "@/shared/config/env"
import { logger } from "@/shared/lib/logger"

const API_BASE = env.NEXT_PUBLIC_API_BASE

export async function fetchRecommendations(
  payload: RecommendRequest
): Promise<RecommendResponse> {
  const res = await fetch(`${API_BASE}/api/v1/recommend`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const text = await res.text()
    logger.error(`Recommendation API failed: ${text}`)
    throw new Error(`Recommendation API failed: ${text}`)
  }

  const responseData = await res.json()
  return responseData
}