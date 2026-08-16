import { Suspense } from "react"
import Link from "next/link"
import { ArrowRight } from "lucide-react"
import {
  TrendingMoviesRow,
  NewReleasesRow,
} from "@/features/movies/components/CatalogRows"
import { MovieRowSkeleton } from "@/features/movies/components/MovieRowSkeleton"
import { Hero } from "@/features/movies/components/Hero"
import { GenreExplorer } from "@/features/movies/components/GenreExplorer"
import { RecommendationBuilder } from "@/features/recommendations/components/RecommendationBuilder"
import { getFeaturedMovie } from "@/features/movies/api"

export const dynamic = "force-dynamic"

export default async function HomePage() {
  let featured = null
  try {
    featured = await getFeaturedMovie()
  } catch {
    featured = null
  }

  return (
    <>
      <Hero movie={featured} />
      <div className="mx-auto w-full max-w-[1440px] px-4 sm:px-6 lg:px-10">
        <RecommendationBuilder />
      </div>
      <Suspense fallback={<MovieRowSkeleton title="Trending this week" />}>
        <TrendingMoviesRow />
      </Suspense>
      <Suspense fallback={<MovieRowSkeleton title="New releases" />}>
        <NewReleasesRow />
      </Suspense>
      <Suspense fallback={null}>
        <GenreExplorer />
      </Suspense>
      <section className="mt-12 border-y border-line bg-panel/45 py-14 sm:mt-16 sm:py-18">
        <div className="mx-auto grid w-full max-w-[1440px] gap-10 px-4 sm:px-6 lg:grid-cols-[0.95fr_1.05fr] lg:px-10">
          <div>
            <span className="text-xs font-bold uppercase tracking-[0.16em] text-crimson">
              The project behind the product
            </span>
            <h2 className="mt-3 max-w-xl font-display text-4xl leading-[0.95] tracking-[-0.04em] text-paper sm:text-5xl">
              Retrieval, ranking, and live movie data—working together.
            </h2>
          </div>
          <div>
            <p className="max-w-2xl text-base leading-7 text-muted">
              M99 is an end-to-end recommendation system built with Next.js,
              FastAPI, MovieLens data, multiple retrievers, reciprocal-rank
              fusion, LightGBM ranking, and TMDB metadata.
            </p>
            <Link
              href="/about"
              className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-crimson transition-colors hover:text-paper"
            >
              See how it works <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
    </>
  )
}
