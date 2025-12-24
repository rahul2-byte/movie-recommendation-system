export interface Movie {
    movieId: number
    title: string
    year: number
    genres: string[]
    rating?: number
    posterUrl?: string
    overview?: string
}  