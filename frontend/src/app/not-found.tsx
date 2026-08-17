import Link from "next/link"

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-[70vh] w-full max-w-7xl flex-col justify-center px-6 py-20 sm:px-10">
      <span className="text-sm font-semibold text-crimson">
        404 / Scene missing
      </span>
      <h1 className="mt-3 font-display text-5xl text-paper sm:text-7xl">
        That page isn&apos;t in this cut.
      </h1>
      <p className="mt-5 max-w-xl text-lg leading-8 text-muted">
        The link may have moved, or the movie is no longer available.
      </p>
      <Link
        href="/"
        className="mt-8 inline-flex min-h-11 w-fit items-center rounded-full bg-crimson px-5 text-sm font-bold text-white transition-colors hover:bg-crimson-bright"
      >
        Return to discover
      </Link>
    </main>
  )
}
