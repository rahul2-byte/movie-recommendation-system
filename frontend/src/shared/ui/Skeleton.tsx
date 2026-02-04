import { HTMLAttributes } from "react"

import { cn } from "@/shared/lib/utils"

function Skeleton({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-surface-strong", className)}
      {...props}
    />
  )
}

export { Skeleton }
