import { Movie } from "@/lib/types/movie"
import { MovieCard } from "./MovieCard"

interface Props {
  title: string
  movies: Movie[]
}

export function MovieRow({ title, movies }: Props) {
  return (
    <section className="mb-10">
      <h2 className="mb-4 text-xl font-semibold">{title}</h2>
      <div className="flex gap-4 overflow-x-auto scrollbar-hide">
        {movies.map((m) => (
          <MovieCard key={m.movieId} movie={m} />
        ))}
      </div>
    </section>
  )
}
