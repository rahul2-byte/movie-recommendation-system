export interface Movie {
  movieId?: number;
  title: string;
  posterUrl?: string;
  year?: number;
  rating?: number | null;
  tmdbId: number;
  genres: string[];
}
