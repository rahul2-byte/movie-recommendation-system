import Link from "next/link"
import { AlertCircle } from "lucide-react"

export function RecommendationsError({ message }: { message: string }) {
  const connectionIssue =
    message.includes("fetch") || message.includes("connect")
  return (
    <main className="mx-auto flex min-h-[65vh] w-full max-w-7xl flex-col justify-center px-6 py-16 sm:px-10">
      <AlertCircle className="size-10 text-danger" />
      <span className="mt-5 text-xs font-bold uppercase tracking-[0.18em] text-crimson">
        Recommendation unavailable
      </span>
      <h1 className="mt-3 font-display text-5xl text-paper sm:text-7xl">
        We couldn&apos;t build your lineup.
      </h1>
      <p className="mt-5 max-w-xl text-lg leading-8 text-muted">
        {connectionIssue
          ? "The discovery engine could not be reached. Check the connection and try again."
          : "The recommendation request failed. Your selected movies are still saved."}
      </p>
      <Link
        href="/#build-lineup"
        className="mt-8 inline-flex min-h-11 w-fit items-center bg-crimson px-5 text-sm font-bold text-white transition-colors hover:bg-crimson-bright"
      >
        Return to your film strip
      </Link>
    </main>
  )
}
