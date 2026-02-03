import { Button } from "@/shared/ui/Button"
import Link from "next/link"

export default function AboutPage() {
  return (
    <div className="container py-24 space-y-16">
      <section className="max-w-3xl">
        <h1 className="text-6xl font-black tracking-tighter mb-8 bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
          Crafting the Future of Cinematic Discovery
        </h1>
        <p className="text-xl text-muted-foreground leading-relaxed">
          Movies99 was born out of a simple frustration: the endless scroll. 
          In an age of infinite content, finding something truly meaningful has become a chore.
        </p>
      </section>

      <div className="grid md:grid-cols-2 gap-12">
        <div className="space-y-4 p-8 rounded-3xl bg-muted/30 border border-border/50">
          <h2 className="text-2xl font-bold">The Vision</h2>
          <p className="text-muted-foreground">
            We use advanced machine learning—specifically Matrix Factorization and Two-Tower architectures—to understand the nuanced relationships between films and your unique taste profile.
          </p>
        </div>
        <div className="space-y-4 p-8 rounded-3xl bg-muted/30 border border-border/50">
          <h2 className="text-2xl font-bold">The Experience</h2>
          <p className="text-muted-foreground">
            Our interface is designed to stay out of your way. Minimal, fast, and elegant. 
            We focus on the metadata that matters: high-fidelity imagery and precise relevancy scores.
          </p>
        </div>
      </div>

      <section className="pt-12">
        <Link href="/">
          <Button size="lg" className="rounded-full">
            Back to Home
          </Button>
        </Link>
      </section>
    </div>
  )
}
