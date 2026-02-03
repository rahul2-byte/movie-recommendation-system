import Link from "next/link"
import { Button } from "@/shared/ui/Button"

export default function NotFound() {
  return (
    <div className="flex min-h-[calc(100vh-80px)] flex-col items-center justify-center p-4 text-center">
      <div className="space-y-2 mb-8">
        <h1 className="text-8xl md:text-9xl font-black italic tracking-tighter text-white/10 select-none">
          404
        </h1>
        <div className="space-y-2 absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <p className="text-2xl md:text-3xl font-black uppercase tracking-[0.2em] text-primary drop-shadow-2xl">
            Scene Not Found
          </p>
          <div className="h-[1px] w-24 bg-primary/50" />
        </div>
      </div>

      <p className="max-w-[400px] text-muted-foreground font-medium text-sm uppercase tracking-widest leading-relaxed mb-10">
        The reel you are looking for has been cut from the final edit or never existed in our archives.
      </p>

      <Link href="/">
        <Button size="lg" className="font-black uppercase tracking-[0.2em] h-14 px-8 rounded-full border border-white/10 hover:bg-white/10 transition-all">
          Return to Studio
        </Button>
      </Link>
    </div>
  )
}