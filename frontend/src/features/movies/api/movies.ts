import { env } from '@/shared/config/env'
import { Movie } from '../types/movie'

export async function searchMovies(

    query: string

): Promise<Movie[]> {

    try {

        const cleanBase = env.NEXT_PUBLIC_API_BASE.replace(/\/$/, "");

        const res = await fetch(

            `${cleanBase}/api/v1/movies/search?q=${query}`

        )



        if (!res.ok) {

            throw new Error(`Movie search failed: ${res.status}`)

        }



        const data = await res.json()

        

        // Backend returns movieId but some parts might expect movie_id.

        // Also ensure posterUrl is correctly mapped if backend uses a different case.

        return data.map((m: any) => ({

            ...m,

            movieId: m.movieId || m.movie_id,

        }))

    } catch (error) {

        console.error("Search API Error:", error)

        return []

    }

}




