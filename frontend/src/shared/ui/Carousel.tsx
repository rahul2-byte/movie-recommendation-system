"use client"

import { useRef } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/shared/ui/Button"

export function Carousel({ children }: { children: React.ReactNode }) {
  const rowRef = useRef<HTMLDivElement>(null)

  const scroll = (dir: "left" | "right") => {
    if (!rowRef.current) return
    const { clientWidth } = rowRef.current
    rowRef.current.scrollBy({
      left: dir === "left" ? -clientWidth : clientWidth,
      behavior: "smooth",
    })
  }

  return (
    <div className="relative">
      <div
        ref={rowRef}
        className="flex gap-grid overflow-x-scroll no-scrollbar scroll-smooth pb-tight"
      >
        {children}
      </div>

      <div className="pointer-events-none absolute inset-y-0 left-0 hidden items-center md:flex">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => scroll("left")}
          className="pointer-events-auto bg-surface-strong/80 backdrop-blur"
        >
          <ChevronLeft className="h-5 w-5" />
        </Button>
      </div>

      <div className="pointer-events-none absolute inset-y-0 right-0 hidden items-center md:flex">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => scroll("right")}
          className="pointer-events-auto bg-surface-strong/80 backdrop-blur"
        >
          <ChevronRight className="h-5 w-5" />
        </Button>
      </div>
    </div>
  )
}
