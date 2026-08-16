import Link from "next/link"
import { getGenres } from "../api"
import type { Genre } from "../types/movie"

export async function GenreExplorer() {
  let genres: Genre[] = []
  try {
    genres = await getGenres()
  } catch {
    return null
  }

  return (
    <section className="py-12 sm:py-16">
      <div className="mx-auto w-full max-w-[1440px] px-4 sm:px-6 lg:px-10">
        <div className="mb-6">
          <div>
            <span className="text-xs font-bold uppercase tracking-[0.16em] text-crimson">
              Choose a direction
            </span>
            <h2 className="mt-2 font-display text-3xl leading-none tracking-[-0.035em] text-paper sm:text-4xl">
              Browse by genre
            </h2>
          </div>
        </div>
        <div className="grid grid-cols-2 border-l border-t border-line sm:grid-cols-3 lg:grid-cols-4">
          {genres.map((genre) => (
            <Link
              key={genre.id}
              href={`/catalog?genre=${genre.id}`}
              className="flex min-h-24 items-center justify-between border-b border-r border-line p-4 text-base font-semibold text-paper transition-colors hover:bg-panel hover:text-crimson"
            >
              <span>{genre.name}</span>
              <span aria-hidden="true">↗</span>
            </Link>
          ))}
        </div>
      </div>
    </section>
  )
}
