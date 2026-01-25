'use client'

import { useRef } from "react"
import { MovieCard } from "./MovieCard"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { CatalogMovie } from "@/lib/api/catalog"

type Props = {
  title: string
  movies: CatalogMovie[]
}

export function MovieRow({ title, movies }: Props) {
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
    <section className="relative space-y-4">
      <h2 className="text-2xl font-semibold">{title}</h2>

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

      <div
        ref={rowRef}
        className="flex gap-4 overflow-x-scroll no-scrollbar scroll-smooth px-10"
      >
        {movies.map((movie) => (
          <MovieCard
            key={movie.tmdbId}   // ✅ REQUIRED
            movie={movie}
          />
        ))}
      </div>
    </section>
  )
}
