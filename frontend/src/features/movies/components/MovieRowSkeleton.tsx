"use client"

import { Skeleton } from "@/shared/ui/Skeleton"

interface MovieRowSkeletonProps {
  title: string
}

export function MovieRowSkeleton({ title }: MovieRowSkeletonProps) {
  return (
    <section className="section">
      <div className="container">
        <div className="flex flex-col gap-2 mb-12">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-10 w-64" />
        </div>
        <div className="flex gap-6 overflow-hidden">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="w-[160px] md:w-[220px] shrink-0">
              <Skeleton className="w-full aspect-[2/3] rounded-md mb-3" />
              <Skeleton className="h-4 w-3/4 mb-1" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
