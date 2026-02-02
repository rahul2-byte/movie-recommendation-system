"use client"

import { useRef } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"

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
        className="flex gap-4 overflow-x-scroll no-scrollbar scroll-smooth"
      >
        {children}
      </div>

      {/* Left button */}
      <button
        onClick={() => scroll("left")}
        className="absolute left-0 top-1/2 z-10 -translate-y-1/2 bg-black/40 p-2 rounded-full hover:bg-black/70 transition"
      >
        <ChevronLeft className="text-white" />
      </button>

      {/* Right button */}
      <button
        onClick={() => scroll("right")}
        className="absolute right-0 top-1/2 z-10 -translate-y-1/2 bg-black/40 p-2 rounded-full hover:bg-black/70 transition"
      >
        <ChevronRight className="text-white" />
      </button>
    </div>
  )
}
