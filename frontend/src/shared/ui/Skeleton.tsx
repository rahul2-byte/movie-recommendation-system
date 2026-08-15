import { HTMLAttributes } from "react"

import { cn } from "@/shared/lib/utils"

function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-[rgba(255,255,255,0.1)]",
        className
      )}
      {...props}
    />
  )
}

export { Skeleton }
