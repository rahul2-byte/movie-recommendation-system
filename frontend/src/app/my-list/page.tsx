import { Button } from "@/shared/ui/Button"
import Link from "next/link"
import { Bookmark } from "lucide-react"
import { PageTransition } from "@/shared/ui/motion/PageTransition"

export default function MyListPage() {
  return (
    <PageTransition>
      <div className="container py-section flex flex-col items-center justify-center text-center space-y-stack">
        <div className="h-icon w-icon rounded-pill bg-surface border border-border flex items-center justify-center">
          <Bookmark className="w-6 h-6 text-muted-foreground" />
        </div>

        <div className="space-y-tight">
          <h1 className="text-h1 font-semibold">Your list is quiet</h1>
          <p className="text-body text-muted-foreground max-w-narrow">
            Save films you want to revisit and they will live here for your next
            movie night.
          </p>
        </div>

        <Link href="/">
          <Button size="lg" variant="outline">
            Discover movies
          </Button>
        </Link>
      </div>
    </PageTransition>
  )
}
