"use client"

import { useMutation } from "@tanstack/react-query"
import { fetchRecommendations } from "@/features/recommendations/api/recommendations"
import { useRecommendationStore } from "@/features/recommendations/store"
import { useRouter } from "next/navigation"

export function useRecommendations() {
  const { setRecommendationPage, setError } = useRecommendationStore()
  const router = useRouter()

  return useMutation({
    mutationFn: fetchRecommendations,
    onSuccess: (data) => {
      setRecommendationPage(data)
      router.push("/recommendations")
    },
    onError: (error) => {
      console.error("Recommendation API Error:", error)
      setError(
        error instanceof Error ? error.message : "An unexpected error occurred"
      )
    },
  })
}
