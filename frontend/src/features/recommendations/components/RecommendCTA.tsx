"use client"

import { useRecommendationStore } from "@/features/recommendations/store"
import { useRecommendations } from "@/features/recommendations/hooks/useRecommendations"
import { Button } from "@/shared/ui/Button"
import { Sparkles, AlertCircle } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

export function RecommendCTA({ onDone }: { onDone: () => void }) {
    const { selectedMovies } = useRecommendationStore()
    const { mutate, isPending, isError, error } = useRecommendations()

    const requiredCount = 5
    const selectedCount = selectedMovies.length
    const isReady = selectedCount === requiredCount

    function handleClick() {
        if (!isReady) return

        const seedMovieIds = selectedMovies.map(movie => movie.movieId)
        
        mutate({
            seed_movie_ids: seedMovieIds,
            moods: [],
            limit: 20,
        }, {
            onSuccess: () => {
                onDone()
            },
        })
    }

    return (
        <div className="space-y-6">
            <AnimatePresence mode="wait">
                {!isReady && (
                    <motion.div 
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="flex items-center gap-3 p-4 bg-primary/10 border border-primary/20 rounded-2xl"
                    >
                        <AlertCircle className="h-5 w-5 text-primary" />
                        <p className="text-sm font-bold text-primary italic">
                            Select exactly {requiredCount} movies to tune the AI ({selectedCount}/{requiredCount})
                        </p>
                    </motion.div>
                )}
            </AnimatePresence>

            <Button
                disabled={!isReady || isPending}
                onClick={handleClick}
                size="lg"
                className="w-full h-16 rounded-2xl font-black uppercase tracking-[0.2em] italic transition-all group overflow-hidden relative bg-primary text-primary-foreground hover:bg-white hover:text-black"
            >
                <div className="relative z-10 flex items-center justify-center gap-3">
                    {isPending ? (
                        <>
                            <div className="animate-spin h-5 w-5 border-2 border-current border-t-transparent rounded-full" />
                            <span>Synchronizing...</span>
                        </>
                    ) : (
                        <>
                            <Sparkles className="h-5 w-5 fill-current group-hover:rotate-12 transition-transform" />
                            <span>Initiate Discovery</span>
                        </>
                    )}
                </div>
                
                {/* Visual feedback glow on ready */}
                {isReady && !isPending && (
                    <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-10 transition-opacity pointer-events-none" />
                )}
            </Button>

            {isError && (
                <div className="text-center space-y-2">
                    <p className="text-xs text-destructive font-black uppercase tracking-widest italic">
                        {error?.message?.includes("fetch") || error?.message?.includes("connect")
                             ? "Connection Lost. Is the backend running?"
                             : "The reel jammed. Please try again."}
                    </p>
                    {error?.message && <p className="text-[10px] text-muted-foreground">{error.message}</p>}
                </div>
            )}
        </div>
    )
}
