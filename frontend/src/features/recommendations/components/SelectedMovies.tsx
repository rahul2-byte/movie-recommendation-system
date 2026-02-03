"use client"

import { useRecommendationStore } from "@/features/recommendations/store"
import { motion, AnimatePresence } from "framer-motion"
import { X } from "lucide-react"

export function SelectedMovies() {
    const { selectedMovies, removeMovie } = useRecommendationStore()

    if (selectedMovies.length === 0) return null

    return (
        <div className="flex flex-wrap gap-3 mt-6">
            <AnimatePresence>
                {selectedMovies.map((movie) => (
                    <motion.div
                        key={movie.movieId}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.8 }}
                        className="flex items-center gap-2 px-4 py-2 bg-accent/30 border border-white/5 rounded-full"
                    >
                        <span className="text-xs font-bold uppercase tracking-wider text-foreground truncate max-w-[150px]">
                            {movie.title}
                        </span>
                        <button
                            onClick={() => removeMovie(movie.movieId)}
                            className="text-muted-foreground hover:text-primary transition-colors"
                        >
                            <X className="h-3 w-3" />
                        </button>
                    </motion.div>
                ))}
            </AnimatePresence>
        </div>
    )
}