import { Movie } from "@/lib/types/movie"

export function normalizeMovie(raw: any): Movie {
    return {
        movieId: raw.movie_id ?? raw.movieId,
        tmdbId: raw.tmdb_id ?? raw.tmdbId ?? null,
        title: raw.title,
        year: raw.year ?? null,
        genres: raw.genres ?? [],
        rating: raw.rating ?? null,
        posterUrl: raw.poster_url ?? raw.posterUrl ?? null,
    }
}
