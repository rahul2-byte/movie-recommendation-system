"use client"

import { useRef, useState, useEffect } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/shared/ui/Button"

export function Carousel({ children }: { children: React.ReactNode }) {
  const rowRef = useRef<HTMLDivElement>(null)
  const [showLeft, setShowLeft] = useState(false)
  const [showRight, setShowRight] = useState(true)

  const checkScroll = () => {
    if (!rowRef.current) return
    const { scrollLeft, scrollWidth, clientWidth } = rowRef.current
    setShowLeft(scrollLeft > 0)
    setShowRight(scrollLeft < scrollWidth - clientWidth - 5)
  }

  useEffect(() => {
    const el = rowRef.current
    if (el) {
      el.addEventListener("scroll", checkScroll)
      checkScroll()
      return () => el.removeEventListener("scroll", checkScroll)
    }
  }, [])

  const scroll = (dir: "left" | "right") => {
    if (!rowRef.current) return
    const scrollAmount = rowRef.current.clientWidth * 0.8

    rowRef.current.scrollBy({
      left: dir === "left" ? -scrollAmount : scrollAmount,
      behavior: "smooth",
    })
  }

  return (
    <div className="group relative">
      <div
        ref={rowRef}
        className="flex gap-4 overflow-x-auto scroll-smooth pb-3 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {children}
      </div>

      <div className="pointer-events-none absolute inset-y-0 left-0 hidden items-center opacity-0 transition-opacity duration-200 group-hover:opacity-100 lg:flex">
        <Button
          variant="ghost"
          size="icon"
          aria-label="Previous movies"
          onClick={() => scroll("left")}
          className={`pointer-events-auto rounded-full border border-line bg-panel/95 text-paper shadow-lg shadow-ink/10 hover:bg-canvas ${!showLeft ? "invisible" : ""}`}
        >
          <ChevronLeft className="h-6 w-6" />
        </Button>
      </div>

      <div className="pointer-events-none absolute inset-y-0 right-0 hidden items-center opacity-0 transition-opacity duration-200 group-hover:opacity-100 lg:flex">
        <Button
          variant="ghost"
          size="icon"
          aria-label="Next movies"
          onClick={() => scroll("right")}
          className={`pointer-events-auto rounded-full border border-line bg-panel/95 text-paper shadow-lg shadow-ink/10 hover:bg-canvas ${!showRight ? "invisible" : ""}`}
        >
          <ChevronRight className="h-6 w-6" />
        </Button>
      </div>
    </div>
  )
}
