import Link from "next/link"
import { ArrowDown, ArrowRight, Star } from "lucide-react"
import type { Movie } from "@/features/movies/types/movie"
import { MovieArtwork } from "./MovieArtwork"

export function Hero({ movie }: { movie: Movie | null }) {
  return (
    <section className="relative isolate min-h-[720px] overflow-hidden bg-canvas sm:min-h-[760px]">
      {movie && (
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
      )}
      <div className="absolute inset-0 bg-[linear-gradient(90deg,#11100f_0%,rgba(17,16,15,0.88)_34%,rgba(17,16,15,0.18)_74%),linear-gradient(0deg,#11100f_0%,transparent_42%)]" />
      <div className="relative z-10 mx-auto flex min-h-[720px] w-full max-w-[1440px] flex-col justify-end px-4 pb-14 pt-32 sm:min-h-[760px] sm:px-6 sm:pb-16 lg:px-10">
        <span className="text-xs font-bold uppercase tracking-[0.16em] text-crimson">
          A recommendation system for movie nights
        </span>
        <h1 className="mt-4 max-w-3xl font-display text-5xl leading-[0.88] tracking-[-0.055em] text-paper sm:text-7xl lg:text-8xl">
          Discover your next favourite film.
        </h1>
        <p className="mt-5 max-w-xl text-base leading-7 text-muted sm:text-lg">
          Start with movies you already love. M99 retrieves, combines, and ranks
          a lineup built around your taste.
        </p>
        <div className="mt-7 flex flex-col gap-3 sm:flex-row">
          <Link
            href="/#build-lineup"
            className="inline-flex min-h-12 items-center justify-center gap-2 bg-crimson px-5 text-sm font-bold text-white transition-colors hover:bg-crimson-bright"
          >
            Build your lineup <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/catalog"
            className="inline-flex min-h-12 items-center justify-center border border-line bg-ink/35 px-5 text-sm font-bold text-paper transition-colors hover:border-muted hover:bg-ink/65"
          >
            Explore movies
          </Link>
        </div>
        {movie && (
          <Link
            href={`/movies/${movie.tmdbId}`}
            className="mt-10 max-w-sm border-l-2 border-crimson pl-4 text-sm text-muted transition-colors hover:text-paper"
          >
            <span className="block text-[0.7rem] font-bold uppercase tracking-[0.14em] text-crimson">
              Featured this week
            </span>
            <strong className="mt-1 block text-base text-paper">
              {movie.title}
            </strong>
            <small className="mt-1 flex items-center gap-1.5">
              {[movie.year, movie.genres?.[0]].filter(Boolean).join(" · ")}
              {movie.rating != null && (
                <em className="inline-flex items-center gap-1 not-italic text-crimson">
                  <Star className="h-3.5 w-3.5 fill-current" />
                  {movie.rating.toFixed(1)}
                </em>
              )}
            </small>
          </Link>
        )}
        <a
          href="#build-lineup"
          className="absolute bottom-8 right-4 hidden items-center gap-2 text-xs font-bold text-muted transition-colors hover:text-paper lg:inline-flex"
          aria-label="Go to recommendation builder"
        >
          <ArrowDown className="h-4 w-4" /> Start discovering
        </a>
      </div>
    </section>
  )
}
