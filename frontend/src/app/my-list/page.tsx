import { Button } from "@/shared/ui/Button"
import Link from "next/link"
import { Bookmark } from "lucide-react"

export default function MyListPage() {
  return (
    <div className="container py-24 flex flex-col items-center justify-center text-center">
      <div className="w-24 h-24 rounded-full bg-zinc-900 border border-white/5 flex items-center justify-center mb-8">
        <Bookmark className="w-10 h-10 text-zinc-500" />
      </div>
      
      <h1 className="text-5xl font-black tracking-tighter mb-4">Your List is Quiet</h1>
      <p className="text-xl text-zinc-400 max-w-md mb-12">
        Save movies you want to watch later and they&apos;ll appear here for your next movie night.
      </p>

      <Link href="/">
        <Button size="lg" className="rounded-full px-10">
          Discover Movies
        </Button>
      </Link>
    </div>
  )
}
