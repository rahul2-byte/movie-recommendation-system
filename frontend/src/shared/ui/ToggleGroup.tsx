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
      className={cn("tag", active ? "tag-selected" : "tag-default")}
    >
      {children}
    </button>
  )
}
