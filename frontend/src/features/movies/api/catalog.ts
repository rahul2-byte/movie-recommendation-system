import type { Movie } from "@/features/movies/types/movie";
import { env } from "@/shared/config/env";
import { logger } from "@/shared/lib/logger";

const API_BASE = env.NEXT_PUBLIC_API_BASE.replace(/\/$/, "");

export async function fetchFromAPI<T>(path: string): Promise<T> {
    const res = await fetch(`${API_BASE}/api/v1${path}`, {
        next: { revalidate: 60 },
    })

    if (!res.ok) {
        logger.error("API failed:", path, res.status)
        throw new Error(`API failed: ${res.status}`)
    }

    return res.json()
}

export function getTrendingMovies(limit = 20) {
    return fetchFromAPI<Movie[]>(`/catalog/trending?limit=${limit}`)
}

export function getPopularMovies(limit = 20) {
    return fetchFromAPI<Movie[]>(`/catalog/popular?limit=${limit}`)
}

export function getNewReleases(limit = 20) {
    return fetchFromAPI<Movie[]>(`/catalog/new?limit=${limit}`)
}