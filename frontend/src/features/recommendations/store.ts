import { create } from "zustand"
import { persist } from "zustand/middleware"
import { RecommendedMovie } from "@/features/recommendations/types"

/* ---------- TYPES ---------- */

export type SelectedMovie = {
  tmdbId: number
  title: string
  posterUrl?: string | null
}

export type Genre = string

type RecommendationState = {
  /* selections */
  selectedGenres: Genre[]
  selectedMovies: SelectedMovie[]

  /* results */
  recommendations: RecommendedMovie[]
  error: string | null

  /* genre actions */
  addGenre: (g: Genre) => void
  removeGenre: (g: Genre) => void

  /* movie actions */
  addMovie: (m: SelectedMovie) => void
  removeMovie: (tmdbId: number) => void
  clearMovies: () => void

  /* recommendation actions */
  setRecommendations: (r: RecommendedMovie[]) => void
  setError: (e: string | null) => void
}

/* ---------- STORE ---------- */

export const useRecommendationStore = create<RecommendationState>()(
  persist(
    (set) => ({
      /* selections */
      selectedGenres: [],
      selectedMovies: [],

      /* results */
      recommendations: [],
      error: null,

      /* genre actions */
      addGenre: (genre) =>
        set((state) =>
          state.selectedGenres.includes(genre)
            ? state
            : { selectedGenres: [...state.selectedGenres, genre] }
        ),

      removeGenre: (genre) =>
        set((state) => ({
          selectedGenres: state.selectedGenres.filter((g) => g !== genre),
        })),

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
      setRecommendations: (recommendations) =>
        set({ recommendations, error: null }),

      setError: (error) => set({ error }),
    }),
    {
      name: "recommendation-storage",
      // The previous persisted state can contain removed mood names. Discard
      // it rather than submitting an invalid request after the clean break.
      version: 2,
    }
  )
)
