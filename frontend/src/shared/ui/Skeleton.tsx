import { HTMLAttributes } from "react"

import { cn } from "@/shared/lib/utils"

function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-xl bg-line/80", className)}
      {...props}
    />
  )
}

export { Skeleton }
