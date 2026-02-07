"use client"

import { useMutation } from "@tanstack/react-query"
import { fetchRecommendations } from "@/features/recommendations/api/recommendations"
import { useRecommendationStore } from "@/features/recommendations/store"
import { useRouter } from "next/navigation"
import { logger } from "@/shared/lib/logger"

export function useRecommendations() {
  const { setRecommendations, setError } = useRecommendationStore()
  const router = useRouter()

  return useMutation({
    mutationFn: fetchRecommendations,
    onSuccess: (data) => {
      setRecommendations(data.recommendations)
      router.push("/recommendations")
    },
    onError: (error) => {
      logger.error("Recommendation API Error:", error)
      setError(error instanceof Error ? error.message : "An unexpected error occurred")
    },
  })
}
