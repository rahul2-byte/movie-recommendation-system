"use client"

import { MovieAutocomplete } from "./MovieAutocomplete"
import { RecommendCTA } from "./RecommendCTA"
import { SelectedMovies } from "./SelectedMovies"

export function RecommendationBuilder() {
  return (
    <section
      id="build-lineup"
      className="my-14 grid scroll-mt-24 overflow-hidden rounded-[1.75rem] border border-line bg-panel shadow-[0_24px_70px_rgba(25,25,28,0.07)] sm:my-20 lg:grid-cols-[0.78fr_1.22fr]"
      aria-labelledby="builder-title"
    >
      <div className="border-b border-line bg-surface-muted p-6 sm:p-9 lg:border-b-0 lg:border-r lg:p-11">
        <h2
          id="builder-title"
          className="font-display text-4xl leading-[0.94] tracking-[-0.04em] text-paper sm:text-5xl"
        >
          What did you love watching?
        </h2>
        <p className="mt-5 max-w-sm leading-7 text-muted">
          Choose one to five movies. M99 will retrieve and rank a new lineup
          around your selections.
        </p>
      </div>
      <div className="p-6 sm:p-9 lg:p-11">
        <MovieAutocomplete />
        <SelectedMovies />
        <RecommendCTA onDone={() => undefined} />
      </div>
    </section>
  )
}
