import Link from "next/link"
import {
  discoverMovies,
  getGenres,
  getNewReleases,
  getPopularMovies,
  getTrendingMovies,
} from "@/features/movies/api"
import { InfiniteCatalogGrid } from "@/features/movies/components/InfiniteCatalogGrid"
import type { Genre, Movie } from "@/features/movies/types/movie"
import { CatalogFilters } from "./CatalogFilters"

type Props = {
  searchParams: Promise<{
    category?: string
    genre?: string
    sort?: "popularity" | "rating" | "newest"
    rating?: string
  }>
}

export default async function CatalogPage({ searchParams }: Props) {
  const params = await searchParams
  const genreId = Number(params.genre) || undefined
  const ratingMin = Number(params.rating) || undefined
  const isDiscovering = Boolean(genreId || params.sort || ratingMin)
  let title = "Trending this week"
  let movies: Movie[] | null = null
  let genres: Genre[] = []

  try {
    genres = await getGenres()
    if (isDiscovering) {
      movies = await discoverMovies({
        genreId,
        ratingMin,
        sort: params.sort ?? "popularity",
        limit: 24,
      })
      title = genreId
        ? (genres.find((genre) => genre.id === genreId)?.name ??
          "Discover movies")
        : "Discover movies"
    } else if (params.category === "popular") {
      movies = await getPopularMovies(24)
      title = "Popular movies"
    } else if (params.category === "new") {
      movies = await getNewReleases(24)
      title = "New releases"
    } else {
      movies = await getTrendingMovies(24)
    }
  } catch {
    movies = null
  }

  return (
    <div className="min-h-[80vh] py-10 sm:py-14">
      <div className="mx-auto w-full max-w-[1440px] px-4 sm:px-6 lg:px-10">
        <header className="flex flex-col justify-between gap-8 border-b border-line pb-8 lg:flex-row lg:items-end">
          <div>
            <span className="text-sm font-semibold text-crimson">
              Browse the catalog
            </span>
            <h1 className="mt-2 font-display text-5xl leading-[0.92] tracking-[-0.055em] text-paper sm:text-7xl">
              {title}
            </h1>
          </div>
          <nav
            aria-label="Catalog categories"
            className="flex gap-6 text-sm font-semibold text-muted"
          >
            <Link
              href="/catalog"
              className={`border-b-2 pb-2 ${!isDiscovering && !params.category ? "border-crimson text-paper" : "border-transparent hover:text-paper"}`}
            >
              Trending
            </Link>
            <Link
              href="/catalog?category=popular"
              className={`border-b-2 pb-2 ${!isDiscovering && params.category === "popular" ? "border-crimson text-paper" : "border-transparent hover:text-paper"}`}
            >
              Popular
            </Link>
            <Link
              href="/catalog?category=new"
              className={`border-b-2 pb-2 ${!isDiscovering && params.category === "new" ? "border-crimson text-paper" : "border-transparent hover:text-paper"}`}
            >
              New releases
            </Link>
          </nav>
        </header>

        <CatalogFilters
          genres={genres}
          genre={params.genre}
          rating={params.rating}
          sort={params.sort}
          resultCount={movies?.length ?? 0}
        />

        {!movies ? (
          <div className="mt-12 grid min-h-64 place-items-center rounded-2xl border border-line bg-panel p-8 text-center">
            <div>
              <h2 className="font-display text-3xl text-paper">
                The catalog is unavailable.
              </h2>
              <p className="mt-3 text-muted">
                Check the connection to the movie service and try again.
              </p>
              <Link
                href="/catalog"
                className="mt-6 inline-flex min-h-11 items-center rounded-full border border-line px-5 text-sm font-bold text-paper hover:border-muted"
              >
                Try again
              </Link>
            </div>
          </div>
        ) : movies.length === 0 ? (
          <div className="mt-12 grid min-h-64 place-items-center rounded-2xl border border-line bg-panel p-8 text-center">
            <div>
              <h2 className="font-display text-3xl text-paper">
                No movies match those filters.
              </h2>
              <p className="mt-3 text-muted">
                Clear a filter to widen the catalog.
              </p>
              <Link
                href="/catalog"
                className="mt-6 inline-flex min-h-11 items-center rounded-full border border-line px-5 text-sm font-bold text-paper hover:border-muted"
              >
                Clear filters
              </Link>
            </div>
          </div>
        ) : (
          <InfiniteCatalogGrid
            initialMovies={movies}
            source={
              isDiscovering
                ? "discover"
                : params.category === "popular"
                  ? "popular"
                  : params.category === "new"
                    ? "new"
                    : "trending"
            }
            filters={{ genreId, ratingMin, sort: params.sort ?? "popularity" }}
          />
        )}
      </div>
    </div>
  )
}
