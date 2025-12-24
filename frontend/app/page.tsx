import { HeroSearch } from "@/components/hero/HeroSearch"
import { MovieRow } from "@/components/movie/MovieRow"

export default function HomePage() {
  return (
    <main>
      <HeroSearch />

      <section className="px-10 py-12 space-y-12">
        <MovieRow title="Trending Now" movies={[]} />
        <MovieRow title="New Releases" movies={[]} />
      </section>
    </main>
  )
}
