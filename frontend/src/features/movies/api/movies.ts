import { Movie } from '../types/movie'
import { apiClient } from '@/shared/api/client'

export async function searchMovies(
    query: string
): Promise<Movie[]> {
    if (query.length < 2) return []
    
    try {
        const data = await apiClient<any[]>(`/movies/search?q=${query}`)
        
        return data.map((m: any) => ({
            ...m,
            movieId: m.movieId || m.movie_id,
        }))
    } catch (error) {
        return []
    }
}




