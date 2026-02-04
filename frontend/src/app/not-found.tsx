import Link from "next/link"
import { Button } from "@/shared/ui/Button"

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-gutter text-center space-y-stack">
      <div className="space-y-tight">
        <h1 className="text-display font-semibold text-muted-foreground/20 select-none">
          404
        </h1>
        <p className="text-h2 font-semibold text-primary">Scene not found</p>
      </div>

      <p className="max-w-narrow text-body text-muted-foreground">
        The page you are looking for has been cut from the final edit or moved
        to a new reel.
      </p>

      <Link href="/">
        <Button size="lg" variant="outline">
          Return to home
        </Button>
      </Link>
    </div>
  )
}
