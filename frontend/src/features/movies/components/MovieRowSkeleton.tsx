"use client"

import { Skeleton } from "@/shared/ui/Skeleton"

interface MovieRowSkeletonProps {
  title: string
}

export function MovieRowSkeleton({ title }: MovieRowSkeletonProps) {
  return (
    <section aria-label={`${title} loading`} className="py-12 sm:py-16">
      <div className="mx-auto w-full max-w-[1440px] px-4 sm:px-6 lg:px-10">
        <div className="flex flex-col gap-2 mb-8">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-10 w-64" />
        </div>
        <div className="flex gap-4 overflow-hidden">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="w-[42vw] max-w-[190px] shrink-0 sm:w-[180px] lg:w-[190px]"
            >
              <Skeleton className="mb-3 aspect-[2/3] w-full" />
              <Skeleton className="h-4 w-3/4 mb-1" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
