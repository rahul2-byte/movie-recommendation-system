import { RecommendationTrigger } from "@/components/recommendation/RecommendationTrigger"

export function Hero() {
  return (
    <section
      className="relative overflow-hidden rounded-3xl border border-[var(--color-bg-muted)] bg-gradient-to-br from-[var(--color-bg-elevated)] to-[var(--color-bg-subtle)] px-10 py-16"
    >
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-semibold tracking-tight">
          Discover movies you’ll actually love
        </h1>

        <p className="mt-4 text-lg text-[var(--color-text-secondary)]">
          Tell us your taste. We’ll handle the recommendations.
        </p>

        <div className="mt-8">
          <RecommendationTrigger />
        </div>
      </div>
    </section>
  )
}
