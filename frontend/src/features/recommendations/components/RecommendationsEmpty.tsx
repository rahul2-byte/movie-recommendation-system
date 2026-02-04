import Link from "next/link"
import { Button } from "@/shared/ui/Button"

export function RecommendationsEmpty() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen text-center px-gutter space-y-stack">
      <h2 className="text-h1 font-semibold">
        No recommendations yet
      </h2>
      <p className="text-body text-muted-foreground max-w-narrow">
        Start a new discovery session to build a reel tailored to your taste.
      </p>
      <Link href="/">
        <Button size="lg">Start discovery</Button>
      </Link>
    </div>
  )
}
