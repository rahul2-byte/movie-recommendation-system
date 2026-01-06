export interface Movie {
    movieId: number
    tmdbId: number | null
    title: string
    year: number | null
    genres: string[]
    rating: number | null
    posterUrl: string | null
}