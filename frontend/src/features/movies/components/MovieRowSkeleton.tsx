"use client"

import { Skeleton } from "@/shared/ui/Skeleton"

interface MovieRowSkeletonProps {
  title: string
}

export function MovieRowSkeleton({ title }: MovieRowSkeletonProps) {
  return (
    <section className="space-y-stack">
      <div className="flex items-center justify-between">
        <h2 className="text-h2 font-semibold">{title}</h2>
      </div>
      <div className="flex gap-grid overflow-hidden no-scrollbar">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="w-poster shrink-0 space-y-tight">
            <Skeleton className="relative aspect-poster rounded-card" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ))}
      </div>
    </section>
  )
}
