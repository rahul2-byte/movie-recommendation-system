"use client"

import { createContext, useContext, useState } from "react"

interface RecommendationContextType {
    seedMovies: number[]
    genres: string[]
    setSeedMovies: (ids: number[]) => void
    setGenres: (genres: string[]) => void
}

const RecommendationContext = createContext<RecommendationContextType | null>(null)

export function RecommendationProvider({ children }: { children: React.ReactNode }) {
    const [seedMovies, setSeedMovies] = useState<number[]>([])
    const [genres, setGenres] = useState<string[]>([])

    return (
        <RecommendationContext.Provider
            value={{ seedMovies, genres, setSeedMovies, setGenres }}
        >
            {children}
        </RecommendationContext.Provider>
    )
}

export function useRecommendation() {
    const ctx = useContext(RecommendationContext)
    if (!ctx) {
        throw new Error("useRecommendation must be used inside RecommendationProvider")
    }
    return ctx
}
