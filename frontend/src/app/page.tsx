import { Suspense } from "react"
import {
  TrendingMoviesRow,
  NewReleasesRow,
} from "@/features/movies/components/CatalogRows"
import { MovieRowSkeleton } from "@/features/movies/components/MovieRowSkeleton"
import { Hero } from "@/features/movies/components/Hero"
import { PageTransition } from "@/shared/ui/motion/PageTransition"

export default function HomePage() {
  return (
    <PageTransition>
      <div className="min-h-screen pb-20">
        <Hero />

        <div className="space-y-12">
          <Suspense fallback={<MovieRowSkeleton title="Trending This Week" />}>
            <TrendingMoviesRow />
          </Suspense>

          <Suspense fallback={<MovieRowSkeleton title="New Releases" />}>
            <NewReleasesRow />
          </Suspense>
        </div>
      </div>
    </PageTransition>
  )
}
