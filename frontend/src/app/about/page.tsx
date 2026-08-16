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
    <main className="mx-auto w-full max-w-7xl px-6 py-16 sm:px-10 lg:py-24">
      <section className="max-w-4xl border-l-2 border-crimson pl-5 sm:pl-8">
        <span className="text-xs font-bold uppercase tracking-[0.18em] text-crimson">
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

      <section className="mt-20 grid border-y border-line sm:grid-cols-2 lg:grid-cols-4">
        <article className="border-b border-line p-6 last:border-b-0 sm:border-r sm:[&:nth-child(2)]:border-r-0 lg:border-b-0 lg:[&:nth-child(2)]:border-r lg:[&:nth-child(4)]:border-r-0">
          <Waypoints className="size-5 text-crimson" />
          <span className="mt-12 block text-xs font-bold uppercase tracking-[0.16em] text-dim">
            Candidate retrieval
          </span>
          <strong className="mt-3 block text-lg text-paper">
            Four complementary retrievers
          </strong>
          <p className="mt-3 text-sm leading-6 text-muted">
            Collaborative, graph, neural, and content signals widen recall.
          </p>
        </article>
        <article className="border-b border-line p-6 last:border-b-0 sm:border-r-0 lg:border-r lg:border-b-0">
          <Layers3 className="size-5 text-crimson" />
          <span className="mt-12 block text-xs font-bold uppercase tracking-[0.16em] text-dim">
            Ordering
          </span>
          <strong className="mt-3 block text-lg text-paper">
            Rank fusion + LightGBM
          </strong>
          <p className="mt-3 text-sm leading-6 text-muted">
            Rank-derived features combine incompatible source score scales.
          </p>
        </article>
        <article className="border-b border-line p-6 last:border-b-0 sm:border-r sm:[&:nth-child(4)]:border-r-0 lg:border-b-0">
          <Database className="size-5 text-crimson" />
          <span className="mt-12 block text-xs font-bold uppercase tracking-[0.16em] text-dim">
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
        <article className="p-6">
          <MonitorPlay className="size-5 text-crimson" />
          <span className="mt-12 block text-xs font-bold uppercase tracking-[0.16em] text-dim">
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
            <span className="text-xs font-bold uppercase tracking-[0.18em] text-crimson">
              Request flow
            </span>
            <h2 className="mt-3 font-display text-4xl text-paper sm:text-5xl">
              How a lineup is created
            </h2>
          </div>
        </div>
        <ol className="mt-10 border-t border-line">
          {stages.map(([number, title, description]) => (
            <li
              key={number}
              className="grid grid-cols-[4rem_1fr] gap-5 border-b border-line py-6 sm:grid-cols-[7rem_1fr]"
            >
              <span className="font-display text-3xl text-crimson">
                {number}
              </span>
              <div>
                <strong className="text-lg text-paper">{title}</strong>
                <p className="mt-2 text-sm leading-6 text-muted">
                  {description}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-24 grid gap-8 border-y border-line py-10 lg:grid-cols-[1fr_1.3fr]">
        <div>
          <span className="text-xs font-bold uppercase tracking-[0.18em] text-crimson">
            Honest by design
          </span>
          <h2 className="mt-3 font-display text-4xl text-paper">
            What this project does not claim
          </h2>
        </div>
        <p className="max-w-2xl text-lg leading-8 text-muted">
          M99 does not claim online learning, production traffic, calibrated
          confidence percentages, persistent user profiles, or measured business
          impact. Raw ranking scores order results; they are not probabilities.
        </p>
      </section>

      <section className="mt-24 flex flex-col items-start justify-between gap-8 border-l-2 border-crimson bg-panel p-8 sm:flex-row sm:items-center sm:p-12">
        <h2 className="max-w-xl font-display text-4xl text-paper sm:text-5xl">
          Build a lineup from movies you love.
        </h2>
        <Link
          href="/#build-lineup"
          className="inline-flex min-h-11 shrink-0 items-center gap-2 bg-crimson px-5 text-sm font-bold text-white transition-colors hover:bg-crimson-bright"
        >
          Start discovering <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </main>
  )
}
