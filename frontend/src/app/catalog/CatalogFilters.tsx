"use client"

import { SlidersHorizontal, X } from "lucide-react"
import { useRouter } from "next/navigation"
import { useTransition } from "react"
import type { Genre } from "@/features/movies/types/movie"

type CatalogFiltersProps = {
  genres: Genre[]
  genre?: string
  rating?: string
  sort?: "popularity" | "rating" | "newest"
  resultCount: number
}

export function CatalogFilters({
  genres,
  genre = "",
  rating = "",
  sort = "popularity",
  resultCount,
}: CatalogFiltersProps) {
  const router = useRouter()
  const [isPending, startTransition] = useTransition()

  function update(name: "genre" | "rating" | "sort", value: string) {
    const values = { genre, rating, sort, [name]: value }
    const params = new URLSearchParams()
    if (values.genre) params.set("genre", values.genre)
    if (values.rating) params.set("rating", values.rating)
    params.set("sort", values.sort)
    startTransition(() => {
      router.replace(`/catalog?${params}`, { scroll: false })
    })
  }

  const filtered = Boolean(genre || rating || sort !== "popularity")

  return (
    <div className="my-8" aria-busy={isPending}>
      <div className="flex flex-col gap-4 rounded-2xl border border-line bg-panel p-4 shadow-sm shadow-ink/5 sm:flex-row sm:flex-wrap sm:items-end">
        <SlidersHorizontal
          className="hidden h-5 w-5 text-crimson sm:block"
          aria-hidden="true"
        />
        <label className="grid min-w-0 flex-1 gap-2 sm:max-w-48">
          <span className="text-xs font-bold text-muted">Genre</span>
          <select
            value={genre}
            onChange={(event) => update("genre", event.target.value)}
            className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson h-11 rounded-xl border border-line bg-canvas px-3 text-sm text-paper focus:border-crimson"
          >
            <option value="">All genres</option>
            {genres.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label className="grid min-w-0 flex-1 gap-2 sm:max-w-48">
          <span className="text-xs font-bold text-muted">Minimum rating</span>
          <select
            value={rating}
            onChange={(event) => update("rating", event.target.value)}
            className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson h-11 rounded-xl border border-line bg-canvas px-3 text-sm text-paper focus:border-crimson"
          >
            <option value="">Any rating</option>
            <option value="6">6+</option>
            <option value="7">7+</option>
            <option value="8">8+</option>
          </select>
        </label>
        <label className="grid min-w-0 flex-1 gap-2 sm:max-w-48">
          <span className="text-xs font-bold text-muted">Sort</span>
          <select
            value={sort}
            onChange={(event) => update("sort", event.target.value)}
            className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson h-11 rounded-xl border border-line bg-canvas px-3 text-sm text-paper focus:border-crimson"
          >
            <option value="popularity">Popularity</option>
            <option value="rating">Rating</option>
            <option value="newest">Newest</option>
          </select>
        </label>
        {filtered && (
          <button
            type="button"
            className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson inline-flex h-11 items-center gap-2 self-end px-3 text-sm font-semibold text-muted hover:text-paper"
            onClick={() => router.replace("/catalog", { scroll: false })}
          >
            <X aria-hidden="true" /> Clear
          </button>
        )}
      </div>
      <p className="mt-3 text-xs text-dim" aria-live="polite">
        {isPending ? "Updating…" : `${resultCount} titles`}
      </p>
    </div>
  )
}
