import { Search } from "lucide-react"
import { searchMovies } from "@/features/movies/api"
import { InfiniteCatalogGrid } from "@/features/movies/components/InfiniteCatalogGrid"

type Props = { searchParams: Promise<{ q?: string }> }

export default async function SearchPage({ searchParams }: Props) {
  const { q = "" } = await searchParams
  let movies = null
  if (q.trim().length >= 2) {
    try {
      movies = await searchMovies(q.trim(), 1, 24)
    } catch {
      movies = null
    }
  }

  return (
    <div className="min-h-[80vh] py-12 sm:py-20">
      <div className="mx-auto w-full max-w-[1440px] px-4 sm:px-6 lg:px-10">
        <header>
          <span className="text-sm font-semibold text-crimson">
            Search the catalog
          </span>
          <h1 className="mt-2 font-display text-5xl leading-[0.92] tracking-[-0.055em] text-paper sm:text-7xl">
            Find a movie
          </h1>
          <form
            role="search"
            className="relative mt-8 flex max-w-3xl flex-col gap-3 sm:flex-row"
          >
            <label htmlFor="catalog-search" className="sr-only">
              Search movies
            </label>
            <Search
              className="pointer-events-none absolute left-4 top-3.5 h-5 w-5 text-dim"
              aria-hidden="true"
            />
            <input
              id="catalog-search"
              name="q"
              defaultValue={q}
              className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson h-12 flex-1 rounded-full border border-line bg-panel pl-12 pr-4 text-paper shadow-sm shadow-ink/5 placeholder:text-dim focus:border-crimson"
              placeholder="Search by title"
              minLength={2}
              required
            />
            <button
              className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson min-h-12 rounded-full bg-crimson px-7 text-sm font-bold text-white hover:bg-crimson-bright active:scale-[0.98]"
              type="submit"
            >
              Search
            </button>
          </form>
        </header>

        {q && movies && movies.length > 0 && (
          <section aria-labelledby="search-results-title">
            <div className="mt-14 mb-6">
              <div>
                <span className="text-sm font-semibold text-crimson">
                  {movies.length} results
                </span>
                <h2
                  id="search-results-title"
                  className="mt-2 font-display text-3xl tracking-[-0.035em] text-paper sm:text-4xl"
                >
                  Results for “{q}”
                </h2>
              </div>
            </div>
            <InfiniteCatalogGrid
              initialMovies={movies}
              source="search"
              query={q.trim()}
            />
          </section>
        )}
        {q && movies?.length === 0 && (
          <div className="mt-12 rounded-2xl border border-line bg-panel p-8">
            <h2 className="font-display text-3xl text-paper">
              We couldn&apos;t find that movie.
            </h2>
            <p className="mt-2 text-muted">
              Check the spelling or try a shorter title.
            </p>
          </div>
        )}
        {q && movies === null && (
          <div className="mt-12 rounded-2xl border border-line bg-panel p-8">
            <h2 className="font-display text-3xl text-paper">
              Search is unavailable.
            </h2>
            <p className="mt-2 text-muted">
              Check the connection to the movie service and try again.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
