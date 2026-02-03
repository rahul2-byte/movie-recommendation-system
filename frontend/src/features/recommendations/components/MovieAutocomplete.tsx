"use client"

import { useState, useRef, useEffect, useMemo } from "react"
import { useRecommendationStore } from "@/features/recommendations/store"
import { MAX_LIKED_MOVIES } from '@/features/recommendations/state'
import { Input } from "@/shared/ui/Input"
import { useMovieSearch } from "@/features/recommendations/hooks/useMovieSearch"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/shared/lib/utils"

export function MovieAutocomplete() {
    const { addMovie, selectedMovies } = useRecommendationStore()
    const { query, setQuery, results, isLoading, isError } = useMovieSearch()
    const [activeIndex, setActiveIndex] = useState(-1)
    const listRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    const canAddMore = selectedMovies.length < MAX_LIKED_MOVIES

    // Deduplicate: Filter out movies that are already selected
    const filteredResults = useMemo(() => {
        if (!results) return []
        return results.filter(
            (movie) => !selectedMovies.some((selected) => selected.movieId === movie.movieId)
        )
    }, [results, selectedMovies])

    // Reset active index when results change
    useEffect(() => {
        setActiveIndex(-1)
    }, [filteredResults])

    // Scroll active item into view
    useEffect(() => {
        if (activeIndex >= 0 && listRef.current) {
            const activeItem = listRef.current.children[activeIndex] as HTMLElement
            if (activeItem) {
                activeItem.scrollIntoView({ block: "nearest", behavior: "smooth" })
            }
        }
    }, [activeIndex])

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (!filteredResults.length) return

        if (e.key === "ArrowDown") {
            e.preventDefault()
            setActiveIndex((prev) => (prev + 1) % filteredResults.length)
        } else if (e.key === "ArrowUp") {
            e.preventDefault()
            setActiveIndex((prev) => (prev - 1 + filteredResults.length) % filteredResults.length)
        } else if (e.key === "Enter") {
            e.preventDefault()
            if (activeIndex >= 0) {
                selectMovie(filteredResults[activeIndex])
            }
        } else if (e.key === "Escape") {
            setQuery("")
        }
    }

    const selectMovie = (movie: any) => {
        addMovie({
            movieId: movie.movieId,
            title: movie.title,
            tmdbId: movie.tmdbId,
        })
        setQuery("")
        setQuery("") // Double ensure clear
        // Keep focus on input
        inputRef.current?.focus()
    }

    return (
        <div className="relative group">
            <Input
                ref={inputRef}
                autoFocus
                disabled={!canAddMore}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={canAddMore ? "Type to search..." : "Selection limit reached"}
                className="h-14 bg-white/5 border-white/10 px-6 rounded-2xl focus:bg-white/10 transition-all font-medium tracking-wide"
                aria-activedescendant={activeIndex >= 0 ? `movie-item-${activeIndex}` : undefined}
                aria-controls="movie-results-list"
                aria-expanded={filteredResults.length > 0}
                role="combobox"
            />

            {isLoading && (
                <div className="absolute right-4 top-4">
                    <div className="animate-spin h-5 w-5 border-2 border-primary border-t-transparent rounded-full" />
                </div>
            )}

            <AnimatePresence>
                {filteredResults.length > 0 && query.length >= 2 && (
                    <motion.div 
                        ref={listRef}
                        id="movie-results-list"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        role="listbox"
                        className="absolute z-50 mt-2 w-full max-h-[300px] overflow-y-auto bg-card border border-border/50 rounded-2xl shadow-2xl scrollbar-thin scrollbar-track-transparent scrollbar-thumb-border/20"
                        onMouseDown={(e) => e.preventDefault()} // Prevent blur on scroll
                    >
                        {filteredResults.map((movie, index) => (
                            <button
                                key={movie.movieId}
                                id={`movie-item-${index}`}
                                role="option"
                                aria-selected={index === activeIndex}
                                onClick={() => selectMovie(movie)}
                                onMouseEnter={() => setActiveIndex(index)}
                                className={cn(
                                    "flex w-full items-center justify-between px-5 py-3 text-left transition-colors border-b border-border/30 last:border-0",
                                    index === activeIndex ? "bg-muted/50" : "hover:bg-muted/30"
                                )}
                            >
                                <div className="flex flex-col gap-0.5 overflow-hidden">
                                    <span className={cn(
                                        "text-sm font-bold uppercase tracking-wider truncate transition-colors",
                                        index === activeIndex ? "text-primary" : "text-muted-foreground"
                                    )}>
                                        {movie.title}
                                    </span>
                                    <div className="flex items-center gap-2 text-[10px] font-medium text-muted-foreground/50 uppercase tracking-widest">
                                        {movie.year && <span>{movie.year}</span>}
                                        {movie.genres && movie.genres.length > 0 && (
                                            <>
                                                <span className="w-0.5 h-0.5 bg-border rounded-full" />
                                                <span className="truncate max-w-[150px]">{movie.genres.slice(0, 2).join(", ")}</span>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </button>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
            
            {isError && (
                <p className="mt-2 text-xs text-destructive font-bold uppercase tracking-widest pl-2">
                    Unable to connect to archive.
                </p>
            )}
        </div>
    )
}