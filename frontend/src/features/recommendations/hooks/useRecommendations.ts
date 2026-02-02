"use client"

import { useMutation } from "@tanstack/react-query"
import { fetchRecommendations } from "@/features/recommendations/api/recommendations"
import { useRecommendationStore } from "@/features/recommendations/store"
import { useRouter } from "next/navigation"

export function useRecommendations() {
  const { setRecommendations } = useRecommendationStore()
  const router = useRouter()

  return useMutation({
    mutationFn: fetchRecommendations,
    onSuccess: (data) => {
      setRecommendations(data.recommendations)
      router.push("/recommendations")
    },
  })
}
