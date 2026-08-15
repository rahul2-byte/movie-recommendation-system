import { Button } from "@/shared/ui/Button"
import Link from "next/link"
import { PageTransition } from "@/shared/ui/motion/PageTransition"

export default function AboutPage() {
  return (
    <PageTransition>
      <div className="container py-section space-y-section">
        <section className="max-w-narrow space-y-stack">
          <p className="text-overline text-muted-foreground/70">
            About the project
          </p>
          <h1 className="text-display font-semibold">
            A portfolio piece built to feel like a real product.
          </h1>
          <p className="text-body-lg text-muted-foreground">
            Movies99 is a personal project that blends machine learning with a
            premium interface. The goal: prove end-to-end product execution with
            a clean, modern visual system.
          </p>
        </section>

        <div className="grid md:grid-cols-2 gap-grid">
          <div className="space-y-tight p-card rounded-xl bg-surface border border-border/60">
            <h2 className="text-h3 font-semibold">The Vision</h2>
            <p className="text-body text-muted-foreground">
              Build a recommendation experience that feels cinematic: curated,
              calm, and confident. Every decision is designed to reduce noise.
            </p>
          </div>
          <div className="space-y-tight p-card rounded-xl bg-surface border border-border/60">
            <h2 className="text-h3 font-semibold">The Experience</h2>
            <p className="text-body text-muted-foreground">
              A bold typographic system, rounded surfaces, and layered lighting
              create a portfolio-grade look that still loads fast and scales.
            </p>
          </div>
        </div>

        <section>
          <Link href="/">
            <Button size="lg" variant="outline">
              Back to home
            </Button>
          </Link>
        </section>
      </div>
    </PageTransition>
  )
}
