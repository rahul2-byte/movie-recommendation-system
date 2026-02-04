import Link from "next/link"
import { Button } from "@/shared/ui/Button"
import { PageTransition } from "@/shared/ui/motion/PageTransition"

export default function ProjectPage() {
  return (
    <PageTransition>
      <main className="container py-section space-y-section">
        <div className="text-center space-y-tight">
          <p className="text-overline text-muted-foreground/70">The System</p>
          <h1 className="text-display font-semibold">
            How the recommendation engine works
          </h1>
          <p className="text-body text-muted-foreground max-w-narrow mx-auto">
            A structured pipeline designed to demonstrate ML reasoning,
            performance tradeoffs, and product alignment.
          </p>
        </div>

        <section className="surface-strong p-card rounded-xl">
          <h2 className="text-h2 font-semibold mb-tight">
            From signal to suggestion
          </h2>
          <p className="text-body text-muted-foreground">
            Movies99 blends collaborative filtering with a modern retrieval
            pipeline to surface a short list of films that closely match your
            taste. We then refine the list for freshness, variety, and
            presentation.
          </p>
        </section>

        <section className="grid md:grid-cols-2 gap-grid">
          <div className="surface p-card rounded-xl space-y-tight">
            <h3 className="text-h3 font-semibold">Multi-stage pipeline</h3>
            <p className="text-body text-muted-foreground">
              A recall, rank, and re-rank flow keeps the system fast while still
              producing high-quality results.
            </p>
            <ul className="list-disc list-inside text-body text-muted-foreground space-y-tight">
              <li>
                Recall uses ALS and two-tower embeddings to build a candidate
                set.
              </li>
              <li>
                Fast retrieval with vector indices keeps response times low.
              </li>
              <li>
                Precision ranking selects the most relevant titles for the reel.
              </li>
            </ul>
          </div>

          <div className="surface p-card rounded-xl space-y-tight">
            <h3 className="text-h3 font-semibold">Rich presentation</h3>
            <p className="text-body text-muted-foreground">
              We enhance ranked MovieLens IDs with TMDB metadata so each
              recommendation includes premium artwork, clear synopsis, and
              relevant tags.
            </p>
            <p className="text-body text-muted-foreground">
              The result is an interface that feels polished and intentional,
              with the model doing the heavy lifting behind the scenes.
            </p>
          </div>
        </section>

        <section className="grid gap-grid md:grid-cols-3">
          <div className="glass rounded-xl p-card">
            <p className="text-overline text-muted-foreground/70">Latency</p>
            <p className="text-h2 font-semibold">Sub-second feel</p>
            <p className="text-body text-muted-foreground">
              Results are cached and optimized to keep the UI snappy while the
              model works in the background.
            </p>
          </div>
          <div className="glass rounded-xl p-card">
            <p className="text-overline text-muted-foreground/70">Quality</p>
            <p className="text-h2 font-semibold">Taste alignment</p>
            <p className="text-body text-muted-foreground">
              Ranking favors relevance, recency, and balance across genres for a
              refined reel.
            </p>
          </div>
          <div className="glass rounded-xl p-card">
            <p className="text-overline text-muted-foreground/70">Delivery</p>
            <p className="text-h2 font-semibold">Portfolio polish</p>
            <p className="text-body text-muted-foreground">
              Every surface is tokenized for consistency, with motion cues that
              reinforce hierarchy.
            </p>
          </div>
        </section>

        <section className="text-center space-y-tight">
          <p className="text-body text-muted-foreground">
            Ready to build your next reel?
          </p>
          <Link href="/">
            <Button size="lg">Get recommendations</Button>
          </Link>
        </section>
      </main>
    </PageTransition>
  )
}
