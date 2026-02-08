import { getTrendingMovies, getPopularMovies, getNewReleases } from "@/features/movies/api"
import { CatalogGrid } from "@/features/movies/components/CatalogGrid"
import { PageTransition } from "@/shared/ui/motion/PageTransition"
import Link from "next/link"
import { ArrowLeft, WifiOff, AlertCircle } from "lucide-react"

type Props = {
  searchParams: Promise<{ category?: string }>
}

export default async function CatalogPage({ searchParams }: Props) {
  const params = await searchParams
  const category = params.category || "trending"
  
  let movies = null
  let title = ""

  try {
    switch (category) {
      case "popular":
        movies = await getPopularMovies(50)
        title = "Popular Hits"
        break
      case "new":
        movies = await getNewReleases(50)
        title = "New Releases"
        break
      default:
        movies = await getTrendingMovies(50)
        title = "Trending This Week"
    }
  } catch (err) {
    movies = null
  }

  return (
    <PageTransition>
      <div className="section pt-32 min-h-screen">
        <div className="container">
          <Link href="/" className="inline-flex items-center gap-2 text-text-muted hover:text-accent transition-colors mb-8 text-sm">
             <ArrowLeft className="w-4 h-4" /> Back to Home
          </Link>

          <div className="mb-12">
            <span className="label-accent">Full Catalog</span>
            <h1 className="heading-section">{title}</h1>
          </div>

          {!movies || movies.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-32 text-center">
              <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mb-6">
                <WifiOff className="w-10 h-10 text-text-muted" />
              </div>
              <h2 className="text-2xl font-serif text-white mb-2">Connection snags.</h2>
              <p className="text-text-muted max-w-md mx-auto mb-8">
                We couldn't reach our cinematic archive. This usually means the backend server is resting or having connection issues.
              </p>
              <Link href="/" className="btn btn-primary">
                Return to Home
              </Link>
            </div>
          ) : (
            <CatalogGrid movies={movies} />
          )}
        </div>
      </div>
    </PageTransition>
  )
}
