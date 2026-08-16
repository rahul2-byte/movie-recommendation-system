import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"
import { ArrowLeft, ExternalLink, Star } from "lucide-react"
import { getMovieDetails, getSimilarMovies } from "@/features/movies/api"
import { MovieArtwork } from "@/features/movies/components/MovieArtwork"
import { InfiniteCatalogGrid } from "@/features/movies/components/InfiniteCatalogGrid"
import type { Movie } from "@/features/movies/types/movie"

type Props = { params: Promise<{ tmdbId: string }> }

async function loadMovie(id: number) {
  try {
    return await getMovieDetails(id)
  } catch {
    return null
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const id = Number((await params).tmdbId)
  const movie = Number.isInteger(id) ? await loadMovie(id) : null
  return movie
    ? {
        title: `${movie.title} | M99`,
        description: movie.overview ?? undefined,
      }
    : { title: "Movie not found | M99" }
}

export default async function MovieDetailsPage({ params }: Props) {
  const id = Number((await params).tmdbId)
  if (!Number.isInteger(id) || id <= 0) notFound()

  const movie = await loadMovie(id)
  if (!movie) notFound()

  let similar: Movie[] = []
  try {
    similar = await getSimilarMovies(id, 24, 1)
  } catch {
    similar = []
  }

  return (
    <main>
      <section className="relative isolate overflow-hidden border-b border-line bg-ink">
        <MovieArtwork
          title={movie.title}
          posterUrl={movie.posterUrl}
          backdropUrl={movie.backdropUrl}
          variant="backdrop"
          priority
          sizes="100vw"
          alt=""
          showFallbackLabel={false}
        />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,#11100f_0%,rgba(17,16,15,0.96)_34%,rgba(17,16,15,0.55)_66%,rgba(17,16,15,0.72)_100%)]" />
        <div className="relative z-10 mx-auto w-full max-w-7xl px-6 py-10 sm:px-10 lg:py-16">
          <Link
            href="/catalog"
            className="inline-flex items-center gap-2 text-sm font-semibold text-muted transition-colors hover:text-paper"
          >
            <ArrowLeft className="h-4 w-4" /> Back to browse
          </Link>
          <div className="mt-10 grid gap-8 md:grid-cols-[minmax(180px,280px)_minmax(0,620px)] md:items-end lg:gap-12">
            <div className="relative aspect-[2/3] max-w-[280px] overflow-hidden border border-line bg-panel shadow-2xl shadow-black/40">
              <MovieArtwork
                title={movie.title}
                posterUrl={movie.posterUrl}
                sizes="(max-width: 640px) 110px, 280px"
                alt={`${movie.title} poster`}
              />
            </div>
            <div className="pb-2">
              <span className="text-xs font-bold uppercase tracking-[0.18em] text-crimson">
                Movie details
              </span>
              <h1 className="mt-4 font-display text-5xl leading-[0.92] text-paper sm:text-7xl">
                {movie.title}
              </h1>
              {movie.tagline && (
                <p className="mt-5 text-xl leading-8 text-muted">
                  {movie.tagline}
                </p>
              )}
              <div className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm font-semibold text-muted">
                {movie.year && <span>{movie.year}</span>}
                {movie.runtime && <span>{movie.runtime} min</span>}
                {movie.rating != null && (
                  <span className="inline-flex items-center gap-1.5 text-paper">
                    <Star className="h-4 w-4 fill-crimson text-crimson" />
                    {movie.rating.toFixed(1)}
                  </span>
                )}
              </div>
              <div className="mt-5 flex flex-wrap gap-2">
                {movie.genres.map((genre) => (
                  <span
                    key={genre}
                    className="border border-line px-3 py-1 text-xs font-semibold text-muted"
                  >
                    {genre}
                  </span>
                ))}
              </div>
              <p className="mt-6 max-w-2xl text-base leading-7 text-muted sm:text-lg sm:leading-8">
                {movie.overview ||
                  "A synopsis is not available for this title."}
              </p>
              {movie.trailerUrl && (
                <a
                  href={movie.trailerUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-7 inline-flex min-h-11 items-center gap-2 bg-crimson px-5 text-sm font-bold text-white transition-colors hover:bg-crimson-bright"
                >
                  Watch trailer <ExternalLink className="h-4 w-4" />
                </a>
              )}
            </div>
          </div>
        </div>
      </section>

      {(movie.director || movie.cast?.length) && (
        <section className="mx-auto grid w-full max-w-7xl gap-8 border-b border-line px-6 py-10 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] sm:px-10">
          {movie.director && (
            <div>
              <span className="block text-xs font-bold uppercase tracking-[0.16em] text-dim">
                Director
              </span>
              <strong className="mt-2 block text-lg text-paper">
                {movie.director}
              </strong>
            </div>
          )}
          {movie.cast?.length ? (
            <div>
              <span className="block text-xs font-bold uppercase tracking-[0.16em] text-dim">
                Top cast
              </span>
              <strong className="mt-2 block text-lg font-normal leading-7 text-paper">
                {movie.cast.join(", ")}
              </strong>
            </div>
          ) : null}
        </section>
      )}

      {similar.length > 0 && (
        <section className="mx-auto w-full max-w-7xl px-6 py-12 sm:px-10 lg:py-16">
          <span className="text-xs font-bold uppercase tracking-[0.16em] text-crimson">
            Keep discovering
          </span>
          <h2 className="mt-3 font-display text-4xl tracking-[-0.04em] text-paper">
            Similar titles
          </h2>
          <div className="mt-8">
            <InfiniteCatalogGrid
              initialMovies={similar}
              source="similar"
              tmdbId={id}
            />
          </div>
        </section>
      )}
    </main>
  )
}
