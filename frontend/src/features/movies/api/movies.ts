import { env } from '@/shared/config/env'
import { Movie } from '../types/movie'

export async function searchMovies(
    query: string
): Promise<Movie[]> {
    const res = await fetch(
        `${env.NEXT_PUBLIC_API_BASE}/api/v1/movies/search?q=${query}`
    )

    if (!res.ok) {
        throw new Error("Movie search failed")
    }

    return res.json()
}