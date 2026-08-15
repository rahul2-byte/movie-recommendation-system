export interface Movie {
  movieId: number
  tmdbId: number
  title: string
  year: number | null
  genres: string[]
  posterUrl: string | null
  // Extended fields for "Netflix" modal
  backdropUrl?: string | null
  overview?: string | null
  tagline?: string | null
  releaseDate?: string | null
  runtime?: number | null
  voteAverage?: number | null
  voteCountTmdb?: number | null
  cast?: string[]
  director?: string | null
  score?: number // Recommendation score
  retrieval_sources?: string[]
  // Legacy/Alternate field mapping
  rating?: number | null
  popularity?: number
}
