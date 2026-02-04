"use client"

import { ReactNode } from "react"
import { cn } from "@/shared/lib/utils"

export function ToggleGroup({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap gap-3">{children}</div>
}

export function ToggleGroupItem({
  children,
  active,
  onClick,
}: {
  children: ReactNode
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-control-x h-control-sm rounded-pill text-overline transition-all border",
        active
          ? "bg-primary border-primary text-primary-foreground shadow-glow scale-105"
          : "bg-transparent border-border text-muted-foreground hover:border-primary/40"
      )}
    >
      {children}
    </button>
  )
}
