// frontend/lib/api/recommend.ts

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
  movie_id: number
  title: string
  score: number
}

export interface RecommendResponse {
  recommendations: RecommendedMovie[]
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE

if (!API_BASE) {
  throw new Error("NEXT_PUBLIC_API_BASE is not defined")
}

export async function fetchRecommendations(
  payload: RecommendRequest
): Promise<RecommendResponse> {
  const res = await fetch(`${API_BASE}/recommend`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Recommendation API failed: ${text}`)
  }

  const responseData = await res.json()
  console.log("Response :- ", responseData)
  return responseData
}
