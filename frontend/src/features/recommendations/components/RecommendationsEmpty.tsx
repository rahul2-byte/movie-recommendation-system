import Link from "next/link"

export function RecommendationsEmpty() {
  return (
    <div className="mx-auto flex min-h-[65vh] w-full max-w-7xl flex-col justify-center px-6 py-16 sm:px-10">
      <span className="text-sm font-semibold text-crimson">No lineup yet</span>
      <h1 className="mt-3 font-display text-5xl text-paper sm:text-7xl">
        Your recommendations will appear here.
      </h1>
      <p className="mt-5 max-w-xl text-lg leading-8 text-muted">
        Choose at least one movie to start a new discovery session.
      </p>
      <Link
        href="/#build-lineup"
        className="mt-8 inline-flex min-h-11 w-fit items-center rounded-full bg-crimson px-5 text-sm font-bold text-white transition-colors hover:bg-crimson-bright"
      >
        Build a lineup
      </Link>
    </div>
  )
}
