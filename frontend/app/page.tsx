import {
  getTrendingMovies,
  getPopularMovies,
  getNewReleases,
} from "@/lib/api/catalog"

import { MovieRow } from "@/components/movie/MovieRow"
import { Hero } from "@/components/hero/Hero"

export default async function HomePage() {
  const [trending, popular, newReleases] = await Promise.all([
    getTrendingMovies(20),
    getPopularMovies(20),
    getNewReleases(20),
  ])

  return (
    <main className="mx-auto max-w-7xl px-6 space-y-16">
      <Hero />
      <MovieRow title="Trending Now" movies={trending} />
      <MovieRow title="Popular" movies={popular} />
      <MovieRow title="New Releases" movies={newReleases} />
    </main>
  )
}
