export type CatalogMovie = {
    tmdbId: number
    title: string
    year: number | null
    genres: string[]
    rating: number | null
    posterUrl: string | null
    overview: string | null
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE!

if (!API_BASE) {
    throw new Error("NEXT_PUBLIC_API_BASE is not defined")
}

export async function fetchFromAPI<T>(path: string): Promise<T | null> {
    try {
        const res = await fetch(`${API_BASE}${path}`, {
            next: { revalidate: 60 },
        })

        if (!res.ok) {
            console.error("API failed:", path, res.status)
            return null
        }

        return res.json()
    } catch (err) {
        console.error("Fetch failed:", path, err)
        return null
    }
}

export function getTrendingMovies(limit = 20) {
    return fetchFromAPI<CatalogMovie[]>(`/catalog/trending?limit=${limit}`)
}

export function getPopularMovies(limit = 20) {
    return fetchFromAPI<CatalogMovie[]>(`/catalog/popular?limit=${limit}`)
}

export function getNewReleases(limit = 20) {
    return fetchFromAPI<CatalogMovie[]>(`/catalog/new?limit=${limit}`)
}
