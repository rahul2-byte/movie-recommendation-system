"use client"

import { useState } from "react"
import { useDebounce } from "use-debounce"
import { useQuery } from "@tanstack/react-query"
import { searchMovies } from "@/features/movies/api/movies"

export function useMovieSearch() {
  const [query, setQuery] = useState("")
  const [debouncedQuery] = useDebounce(query, 300)

  const { data, isLoading, isError } = useQuery({
    queryKey: ["movie-search", debouncedQuery],
    queryFn: () => searchMovies(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
  })

  return {
    query,
    setQuery,
    results: data,
    isLoading,
    isError,
  }
}
