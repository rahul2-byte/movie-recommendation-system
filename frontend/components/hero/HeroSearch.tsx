"use client"

import { useRecommendationStore } from "@/lib/store/recommendationStore"

export function HeroSearch() {
  const { setGenres } = useRecommendationStore()

  return (
    <div className="relative flex h-[70vh] flex-col items-center justify-center text-center">
      <h1 className="text-5xl font-bold">
        Find your next <span className="text-pink-500">favorite story</span>
      </h1>

      <p className="mt-4 text-gray-300">
        Discover top-rated movies and hidden gems curated just for you.
      </p>

      <div className="mt-8 flex w-full max-w-2xl">
        <input
          className="flex-1 rounded-l-full bg-neutral-800 px-6 py-4 outline-none"
          placeholder="Search for movies, TV shows, or actors..."
        />
        <button className="rounded-r-full bg-pink-500 px-6 font-semibold">
          Search
        </button>
      </div>
    </div>
  )
}
