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
        "min-h-10 rounded-full border px-4 text-sm font-semibold transition-colors active:scale-[0.98]",
        active
          ? "border-crimson bg-crimson text-white"
          : "border-line bg-panel text-muted hover:text-paper"
      )}
    >
      {children}
    </button>
  )
}
