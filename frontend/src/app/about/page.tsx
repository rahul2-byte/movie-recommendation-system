import Link from "next/link"
import {
  ArrowRight,
  Database,
  Layers3,
  MonitorPlay,
  Waypoints,
} from "lucide-react"

const stages = [
  ["01", "Choose seeds", "Select one to five movies you already enjoy."],
  [
    "02",
    "Retrieve candidates",
    "ALS, item graph, two-tower, and content models find candidates.",
  ],
  [
    "03",
    "Fuse and rank",
    "Reciprocal-rank fusion combines sources before LightGBM orders the lineup.",
  ],
  [
    "04",
    "Enrich results",
    "TMDB adds current posters, details, cast, and trailers.",
  ],
]

export default function AboutPage() {
  return (
    <main className="mx-auto w-full max-w-7xl px-6 py-14 sm:px-10 lg:py-20">
      <section className="max-w-4xl">
        <span className="text-sm font-semibold text-crimson">
          About the engine
        </span>
        <h1 className="mt-4 font-display text-5xl leading-[0.95] text-paper sm:text-7xl">
          A recommendation project designed as a real product.
        </h1>
        <p className="mt-7 max-w-3xl text-lg leading-8 text-muted">
          M99 answers a practical question: what should you watch next based on
          movies you already like? It connects an offline-trained retrieval and
          ranking pipeline to a responsive discovery interface.
        </p>
      </section>

      <section className="mt-20 grid gap-3 sm:grid-cols-2 lg:grid-cols-12">
        <article className="rounded-2xl bg-panel p-7 shadow-sm shadow-ink/5 lg:col-span-7">
          <Waypoints className="size-5 text-crimson" />
          <span className="mt-16 block text-sm font-semibold text-muted">
            Candidate retrieval
          </span>
          <strong className="mt-3 block text-lg text-paper">
            Four complementary retrievers
          </strong>
          <p className="mt-3 text-sm leading-6 text-muted">
            Collaborative, graph, neural, and content signals widen recall.
          </p>
        </article>
        <article className="rounded-2xl bg-surface-muted p-7 lg:col-span-5">
          <Layers3 className="size-5 text-crimson" />
          <span className="mt-16 block text-sm font-semibold text-muted">
            Ordering
          </span>
          <strong className="mt-3 block text-lg text-paper">
            Rank fusion + LightGBM
          </strong>
          <p className="mt-3 text-sm leading-6 text-muted">
            Rank-derived features combine incompatible source score scales.
          </p>
        </article>
        <article className="rounded-2xl bg-accent-soft p-7 lg:col-span-5">
          <Database className="size-5 text-crimson" />
          <span className="mt-16 block text-sm font-semibold text-muted">
            Data
          </span>
          <strong className="mt-3 block text-lg text-paper">
            MovieLens + TMDB
          </strong>
          <p className="mt-3 text-sm leading-6 text-muted">
            Historical interactions train the system; TMDB supplies display
            metadata.
          </p>
        </article>
        <article className="rounded-2xl bg-panel p-7 shadow-sm shadow-ink/5 lg:col-span-7">
          <MonitorPlay className="size-5 text-crimson" />
          <span className="mt-16 block text-sm font-semibold text-muted">
            Experience
          </span>
          <strong className="mt-3 block text-lg text-paper">
            Next.js + FastAPI
          </strong>
          <p className="mt-3 text-sm leading-6 text-muted">
            A typed web client calls a bundle-backed recommendation API.
          </p>
        </article>
      </section>

      <section className="mt-24 max-w-4xl">
        <div>
          <div>
            <h2 className="font-display text-4xl text-paper sm:text-5xl">
              How a lineup is created
            </h2>
          </div>
        </div>
        <ol className="mt-10 border-t border-line">
          {stages.map(([, title, description]) => (
            <li
              key={title}
              className="grid gap-2 border-b border-line py-6 sm:grid-cols-[minmax(12rem,0.7fr)_1fr] sm:gap-8"
            >
              <strong className="text-lg text-paper">{title}</strong>
              <p className="text-sm leading-6 text-muted">{description}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-24 grid gap-8 rounded-[1.75rem] bg-surface-muted p-8 lg:grid-cols-[1fr_1.3fr] lg:p-12">
        <div>
          <h2 className="font-display text-4xl text-paper">
            What this project does not claim
          </h2>
        </div>
        <p className="max-w-2xl text-lg leading-8 text-muted">
          M99 does not claim online learning, production traffic, calibrated
          confidence percentages, persistent user profiles, or measured business
          impact. Raw ranking scores order results; they are not probabilities.
        </p>
      </section>

      <section className="mt-24 flex flex-col items-start justify-between gap-8 rounded-[1.75rem] bg-crimson p-8 sm:flex-row sm:items-center sm:p-12">
        <h2 className="max-w-xl font-display text-4xl text-white sm:text-5xl">
          Build a lineup from movies you love.
        </h2>
        <Link
          href="/#build-lineup"
          className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson inline-flex min-h-11 shrink-0 items-center gap-2 rounded-full bg-white px-5 text-sm font-bold text-ink transition-colors hover:bg-canvas active:scale-[0.98]"
        >
          Start discovering <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </main>
  )
}
