import { Skeleton } from "@/shared/ui/Skeleton"

export default function Loading() {
  return (
    <div className="container py-10 space-y-24">
      <section className="h-[70vh] w-full rounded-[2.5rem] bg-zinc-900/50 animate-pulse" />
      
      <div className="space-y-12">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="space-y-6">
            <Skeleton className="h-10 w-48" />
            <div className="flex gap-6 overflow-hidden">
              {[...Array(6)].map((_, j) => (
                <Skeleton key={j} className="aspect-[2/3] w-[180px] shrink-0 rounded-2xl" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
