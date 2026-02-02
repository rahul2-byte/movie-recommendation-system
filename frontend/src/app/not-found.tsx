import Link from "next/link"
import { Button } from "@/shared/ui/Button"

export default function NotFound() {
  return (
    <div className="flex min-h-[80vh] flex-col items-center justify-center px-6 text-center space-y-10">
      <div className="relative">
        <h1 className="text-[12rem] font-black text-primary/10 leading-none">404</h1>
        <div className="absolute inset-0 flex items-center justify-center">
          <h2 className="text-5xl font-black uppercase tracking-tighter">Lost in Space</h2>
        </div>
      </div>
      
      <p className="text-2xl text-muted-foreground max-w-lg font-bold">
        This page was deleted from the script. Let&apos;s get you back to the main feature.
      </p>

      <Link href="/">
        <Button size="lg" className="rounded-full px-12 h-16 text-xl font-black uppercase italic hover:skew-x-[-10deg] transition-transform">
          Back to Home
        </Button>
      </Link>
    </div>
  )
}
