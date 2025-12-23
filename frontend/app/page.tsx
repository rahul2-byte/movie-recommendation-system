import { HeroSearch } from "@/components/hero/HeroSearch"
import { MovieRow } from "@/components/movie/MovieRow"

export default function HomePage() {
  return (
    <main>
      <HeroSearch />

      <div className="px-10">
        <MovieRow title="Trending Now" movies={[]} />
        <MovieRow title="New Releases" movies={[]} />
      </div>
    </main>
  )
}
