import { create } from "zustand"
import { persist } from "zustand/middleware"
import {
  RecommendedMovie,
  RecommendResponse,
} from "@/features/recommendations/types"

/* ---------- TYPES ---------- */

export type SelectedMovie = {
  tmdbId: number
  title: string
  posterUrl?: string | null
}

type RecommendationState = {
  selectedMovies: SelectedMovie[]

  /* results */
  recommendations: RecommendedMovie[]
  recommendationSessionId: string | null
  recommendationNextOffset: number | null
  recommendationHasMore: boolean
  error: string | null

  /* movie actions */
  addMovie: (m: SelectedMovie) => void
  removeMovie: (tmdbId: number) => void
  clearMovies: () => void

  /* recommendation actions */
  setRecommendationPage: (response: RecommendResponse) => void
  appendRecommendationPage: (response: RecommendResponse) => void
  setError: (e: string | null) => void
}

export function migrateRecommendationStorage(persistedState: unknown) {
  const saved =
    persistedState && typeof persistedState === "object" ? persistedState : {}
  return {
    ...saved,
    recommendationSessionId: null,
    recommendationNextOffset: null,
    recommendationHasMore: false,
    error: null,
  }
}

/* ---------- STORE ---------- */

export const useRecommendationStore = create<RecommendationState>()(
  persist(
    (set) => ({
      selectedMovies: [],

      /* results */
      recommendations: [],
      recommendationSessionId: null,
      recommendationNextOffset: null,
      recommendationHasMore: false,
      error: null,

      /* movie actions */
      addMovie: (movie) =>
        set((state) => {
          if (
            state.selectedMovies.length >= 5 ||
            state.selectedMovies.some((m) => m.tmdbId === movie.tmdbId)
          ) {
            return state
          }
          return { selectedMovies: [...state.selectedMovies, movie] }
        }),

      removeMovie: (id) =>
        set((state) => ({
          selectedMovies: state.selectedMovies.filter((m) => m.tmdbId !== id),
        })),

      clearMovies: () => set({ selectedMovies: [] }),

      /* recommendation actions */
      setRecommendationPage: (response) =>
        set({
          recommendations: response.recommendations,
          recommendationSessionId: response.sessionId,
          recommendationNextOffset: response.nextOffset,
          recommendationHasMore: response.hasMore,
          error: null,
        }),

      appendRecommendationPage: (response) =>
        set((state) => {
          const knownIds = new Set(
            state.recommendations.map((movie) => movie.tmdbId)
          )
          return {
            recommendations: [
              ...state.recommendations,
              ...response.recommendations.filter(
                (movie) => !knownIds.has(movie.tmdbId)
              ),
            ],
            recommendationNextOffset: response.nextOffset,
            recommendationHasMore: response.hasMore,
          }
        }),

      setError: (error) => set({ error }),
    }),
    {
      name: "recommendation-storage",
      // The previous persisted state can contain removed mood names. Discard
      // it rather than submitting an invalid request after the clean break.
      version: 4,
      migrate: migrateRecommendationStorage,
    }
  )
)
