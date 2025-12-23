import { create } from "zustand"
import { Movie } from "@/lib/types/movie"

interface RecommendationState {
  seeds: number[]
  genres: string[]
  results: Movie[]
  setSeeds: (ids: number[]) => void
  setGenres: (genres: string[]) => void
  setResults: (movies: Movie[]) => void
}

export const useRecommendationStore = create<RecommendationState>((set) => ({
  seeds: [],
  genres: [],
  results: [],
  setSeeds: (seeds) => set({ seeds }),
  setGenres: (genres) => set({ genres }),
  setResults: (results) => set({ results }),
}))
