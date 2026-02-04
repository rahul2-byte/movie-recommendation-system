import Link from "next/link"
import { Button } from "@/shared/ui/Button"
import { AlertCircle } from "lucide-react"

export function RecommendationsError({ message }: { message: string }) {
  const isConnectionIssue =
    message.includes("fetch") || message.includes("connect")

  return (
    <div className="flex flex-col items-center justify-center min-h-screen text-center px-gutter space-y-stack">
      <div className="p-4 bg-destructive/10 rounded-pill">
        <AlertCircle className="w-10 h-10 text-destructive" />
      </div>
      <h2 className="text-h1 font-semibold">
        We could not load your reel
      </h2>
      <p className="text-body text-muted-foreground max-w-narrow">
        {isConnectionIssue
          ? "Unable to reach the discovery engine. Please check the backend service."
          : "Something went wrong while preparing your recommendations."}
      </p>
      <Link href="/">
        <Button variant="outline" size="lg">
          Return home
        </Button>
      </Link>
    </div>
  )
}
