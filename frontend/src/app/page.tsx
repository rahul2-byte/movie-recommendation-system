import { getTrendingMovies, getPopularMovies, getNewReleases } from "@/features/movies/api"

import { MovieRow } from "@/features/movies/components/MovieRow"
import { Hero } from "@/features/movies/components/Hero"
import { PageTransition } from "@/shared/ui/motion/PageTransition"

export default async function HomePage() {
  const [trending, popular, newReleases] = await Promise.all([
    getTrendingMovies(20),
    getPopularMovies(20),
    getNewReleases(20),
  ])

  return (
    <PageTransition>
      <div className="container py-page space-y-section">
        <Hero />
        <section className="space-y-stack">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div className="space-y-tight max-w-narrow">
              <p className="text-overline text-muted-foreground/70">
                Portfolio highlights
              </p>
              <h2 className="text-h1 font-semibold">
                A full-stack recommendation system in production quality.
              </h2>
            </div>
            <p className="text-body text-muted-foreground max-w-narrow">
              Built to demonstrate model design, API architecture, and a premium
              UI system in a single cohesive product.
            </p>
          </div>

          <div className="grid gap-grid md:grid-cols-3">
            <div className="surface rounded-xl p-card space-y-tight">
              <p className="text-overline text-muted-foreground/70">Experience</p>
              <p className="text-h3 font-semibold">Curated discovery</p>
              <p className="text-body text-muted-foreground">
                Minimal interface, decisive choices, and movie cards tuned for
                quick scanning.
              </p>
            </div>
            <div className="surface rounded-xl p-card space-y-tight">
              <p className="text-overline text-muted-foreground/70">Engine</p>
              <p className="text-h3 font-semibold">Hybrid ML pipeline</p>
              <p className="text-body text-muted-foreground">
                Recall + ranking flow engineered for quality and speed at
                portfolio scale.
              </p>
            </div>
            <div className="surface rounded-xl p-card space-y-tight">
              <p className="text-overline text-muted-foreground/70">Craft</p>
              <p className="text-h3 font-semibold">Design system</p>
              <p className="text-body text-muted-foreground">
                Tokenized typography, spacing, and rounded surfaces for a
                polished feel.
              </p>
            </div>
          </div>
        </section>

        <div className="space-y-section pb-section">
          <MovieRow title="Trending now" movies={trending} />
          <MovieRow title="Popular hits" movies={popular} />
          <MovieRow title="Fresh arrivals" movies={newReleases} />
        </div>

        <section className="grid gap-grid lg:grid-cols-[1.1fr_0.9fr] items-center">
          <div className="space-y-stack">
            <p className="text-overline text-muted-foreground/70">Behind the scenes</p>
            <h2 className="text-h1 font-semibold">
              Built as a portfolio-grade case study.
            </h2>
            <p className="text-body text-muted-foreground">
              Movies99 showcases the ability to define product goals, build an
              ML-powered backend, and ship a front-end with strong visual
              hierarchy and thoughtful motion.
            </p>
            <div className="grid gap-grid sm:grid-cols-2">
              <div className="surface rounded-lg p-card">
                <p className="text-overline text-muted-foreground/70">Focus area</p>
                <p className="text-body font-semibold">Recommendation UX</p>
              </div>
              <div className="surface rounded-lg p-card">
                <p className="text-overline text-muted-foreground/70">Result</p>
                <p className="text-body font-semibold">Premium product feel</p>
              </div>
            </div>
          </div>
          <div className="glass rounded-xl p-card shadow-hero space-y-tight">
            <p className="text-overline text-muted-foreground/70">Tech stack</p>
            <ul className="space-y-tight text-body text-muted-foreground">
              <li>Next.js 16 · App Router · Tailwind v4</li>
              <li>FastAPI services + vector retrieval</li>
              <li>ALS + ranking models for personalization</li>
              <li>TMDB enrichment and optimized imagery</li>
            </ul>
          </div>
        </section>
      </div>
    </PageTransition>
  )
}
