export interface Movie {
  movieId: number
  tmdbId: number
  title: string
  year: number | null
  genres: string[]
  posterUrl: string | null
  backdropUrl?: string | null
  overview?: string | null
  tagline?: string | null
  releaseDate?: string | null
  runtime?: number | null
  voteAverage?: number | null
  voteCountTmdb?: number | null
  cast?: string[]
  director?: string | null
  trailerUrl?: string | null
  voteCount?: number | null
  rankScore?: number
  rating?: number | null
  popularity?: number
}

export interface Genre {
  id: number
  name: string
}
