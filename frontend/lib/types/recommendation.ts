
export interface RecommendationRequest {
    seed_movies: number[]
    genres: string[]
    limit?: number
}

export interface RecommendedMovie {
    movieId: number
    title: string
    year?: number
    posterUrl?: string
    rating?: number
}
