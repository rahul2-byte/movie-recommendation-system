import { Movie } from '@/lib/types/movie'

export async function searchMovies(
    query: string
): Promise<Movie[]> {
    const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE}/movies/search?q=${query}`
    )

    if (!res.ok) {
        throw new Error("Movie search failed")
    }

    return res.json()
}
