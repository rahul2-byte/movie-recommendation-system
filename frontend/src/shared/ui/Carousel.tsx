"use client"

import { useRef, useState, useEffect } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/shared/ui/Button"

export function Carousel({ children }: { children: React.ReactNode }) {
  const rowRef = useRef<HTMLDivElement>(null)
  const [showLeft, setShowLeft] = useState(false)
  const [, setShowRight] = useState(true)

  const checkScroll = () => {
    if (!rowRef.current) return
    const { scrollLeft, scrollWidth, clientWidth } = rowRef.current
    setShowLeft(scrollLeft > 0)
    // Allow a small buffer (5px) for rounding errors
    setShowRight(scrollLeft < scrollWidth - clientWidth - 5)
  }

  useEffect(() => {
    const el = rowRef.current
    if (el) {
      el.addEventListener("scroll", checkScroll)
      // Check initial state
      checkScroll()
      return () => el.removeEventListener("scroll", checkScroll)
    }
  }, [])

  const scroll = (dir: "left" | "right") => {
    if (!rowRef.current) return
    const { clientWidth, scrollLeft, scrollWidth } = rowRef.current

    // Infinite scroll logic for buttons
    if (dir === "right" && scrollLeft >= scrollWidth - clientWidth - 5) {
      // If at end, loop to start
      rowRef.current.scrollTo({ left: 0, behavior: "smooth" })
      return
    }

    if (dir === "left" && scrollLeft <= 0) {
      // If at start, loop to end (optional, usually confusing, but let's just stick to standard scroll left)
      // rowRef.current.scrollTo({ left: scrollWidth, behavior: "smooth" })
      // For now, let's just scroll left normally.
    }

    const scrollAmount = clientWidth * 0.8 // Scroll 80% of view

    rowRef.current.scrollBy({
      left: dir === "left" ? -scrollAmount : scrollAmount,
      behavior: "smooth",
    })
  }

  return (
    <div className="relative group">
      <div
        ref={rowRef}
        className="flex gap-8 overflow-x-auto no-scrollbar scroll-smooth pb-4 px-6 md:px-0"
      >
        {children}
      </div>

      <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center transition-opacity duration-300 opacity-0 group-hover:opacity-100">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => scroll("left")}
          className={`pointer-events-auto bg-black/50 hover:bg-black/80 text-white backdrop-blur rounded-full w-12 h-12 border border-white/10 ${!showLeft ? "invisible" : ""}`}
        >
          <ChevronLeft className="h-6 w-6" />
        </Button>
      </div>

      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center transition-opacity duration-300 opacity-0 group-hover:opacity-100">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => scroll("right")}
          className="pointer-events-auto bg-black/50 hover:bg-black/80 text-white backdrop-blur rounded-full w-12 h-12 border border-white/10"
        >
          <ChevronRight className="h-6 w-6" />
        </Button>
      </div>
    </div>
  )
}
