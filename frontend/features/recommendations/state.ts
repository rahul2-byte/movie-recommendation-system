import { Mood } from "@/lib/types/mood"

export interface RecommendationState {
    genres: string[]
    moods: Mood[]
    likedMovies: {
        movieId: number
        tmdbId: number | null
        title: string
    }[]
}

export const MAX_LIKED_MOVIES = 5
