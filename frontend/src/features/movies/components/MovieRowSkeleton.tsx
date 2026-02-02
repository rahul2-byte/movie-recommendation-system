"use client"

import { Skeleton } from "@/shared/ui/Skeleton"

interface MovieRowSkeletonProps {
  title: string
}

export function MovieRowSkeleton({ title }: MovieRowSkeletonProps) {
  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">{title}</h2>
      </div>
      <div className="flex gap-6 overflow-hidden no-scrollbar">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="w-[180px] shrink-0 space-y-3">
            <Skeleton className="relative aspect-[2/3] rounded-2xl" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ))}
      </div>
    </section>
  )
}
