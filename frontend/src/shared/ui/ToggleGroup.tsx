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
                "px-6 py-3 rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] transition-all border-2",
                active
                    ? "bg-primary border-primary text-primary-foreground shadow-lg shadow-primary/20 scale-105"
                    : "bg-transparent border-white/5 text-muted-foreground hover:border-white/20"
            )}
        >
            {children}
        </button>
    )
}