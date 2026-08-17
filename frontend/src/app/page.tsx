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
import { getFeaturedMovie, getTrendingMovies } from "@/features/movies/api"
import type { Movie } from "@/features/movies/types/movie"

export const dynamic = "force-dynamic"

export default async function HomePage() {
  let featured = null
  let trending: Movie[] = []
  try {
    const [featuredMovie, trendingMovies] = await Promise.all([
      getFeaturedMovie(),
      getTrendingMovies(8),
    ])
    featured = featuredMovie
    trending = trendingMovies
  } catch {
    featured = null
    trending = []
  }

  return (
    <>
      <Hero
        movie={featured}
        movies={trending.length ? trending : featured ? [featured] : []}
      />
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
      <section className="mt-12 py-14 sm:mt-16 sm:py-18">
        <div className="mx-auto grid w-full max-w-[1440px] gap-8 px-4 sm:px-6 lg:grid-cols-[1.15fr_0.85fr] lg:items-end lg:px-10">
          <div>
            <h2 className="max-w-2xl font-display text-4xl leading-[0.95] tracking-[-0.04em] text-paper sm:text-5xl">
              Retrieval, ranking, and live movie data working together.
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
