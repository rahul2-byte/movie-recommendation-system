"use client"

import { MovieAutocomplete } from "./MovieAutocomplete"
import { RecommendCTA } from "./RecommendCTA"
import { SelectedMovies } from "./SelectedMovies"

export function RecommendationBuilder() {
  return (
    <section
      id="build-lineup"
      className="my-12 grid scroll-mt-20 border border-line bg-panel/50 sm:my-16 lg:grid-cols-[0.85fr_1.15fr]"
      aria-labelledby="builder-title"
    >
      <div className="border-b border-line p-6 sm:p-8 lg:border-b-0 lg:border-r lg:p-10">
        <span className="text-xs font-bold uppercase tracking-[0.16em] text-crimson">
          Start with what you know
        </span>
        <h2
          id="builder-title"
          className="mt-3 font-display text-4xl leading-[0.92] tracking-[-0.04em] text-paper sm:text-5xl"
        >
          What did you love watching?
        </h2>
        <p className="mt-5 max-w-sm leading-7 text-muted">
          Choose one to five movies. M99 will retrieve and rank a new lineup
          around your selections.
        </p>
      </div>
      <div className="p-6 sm:p-8 lg:p-10">
        <MovieAutocomplete />
        <SelectedMovies />
        <RecommendCTA onDone={() => undefined} />
      </div>
    </section>
  )
}
