import {
  getTrendingMovies,
  getPopularMovies,
  getNewReleases,
} from "@/features/catalog/api"

import { MovieRow } from "@/features/movies/components/MovieRow"
import { Hero } from "@/features/movies/components/Hero"

export default async function HomePage() {
  const [trending, popular, newReleases] = await Promise.all([
    getTrendingMovies(20),
    getPopularMovies(20),
    getNewReleases(20),
  ])

  return (
    <div className="container py-10 space-y-24">
      <Hero />
      <div className="space-y-24 pb-20">
        <MovieRow title="Trending Now" movies={trending} />
        <MovieRow title="Popular Hits" movies={popular} />
        <MovieRow title="Fresh Arrivals" movies={newReleases} />
      </div>
    </div>
  )
}