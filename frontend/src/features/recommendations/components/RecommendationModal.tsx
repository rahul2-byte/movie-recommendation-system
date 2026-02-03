"use client"

import { GenreSelector } from "./GenreSelector"
import { MovieAutocomplete } from "./MovieAutocomplete"
import { SelectedMovies } from "./SelectedMovies"
import { RecommendCTA } from "./RecommendCTA"
import { Modal } from "@/shared/ui/Modal"
import { ModalCloseButton } from "@/shared/ui/ModalCloseButton"
import { motion, AnimatePresence } from "framer-motion"
import { useRecommendationStore } from "@/features/recommendations/store"

export function RecommendationModal({
    onClose,
}: {
    onClose: () => void
}) {
    const { selectedMovies } = useRecommendationStore()
    const moviesNeeded = 5 - selectedMovies.length

    return (
        <Modal>
            <div className="flex flex-col space-y-8">
                <header className="flex items-start justify-between">
                    <div className="space-y-2">
                        <h2 className="text-4xl md:text-5xl font-black tracking-tighter text-white uppercase italic leading-none">
                            Define Your <span className="text-primary drop-shadow-[0_0_20px_rgba(249,177,122,0.3)]">Taste</span>
                        </h2>
                        
                        <AnimatePresence mode="wait">
                            <motion.p 
                                key={moviesNeeded}
                                initial={{ opacity: 0, y: 5 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -5 }}
                                className="text-white/40 text-[10px] font-bold uppercase tracking-[0.3em] italic"
                            >
                                {moviesNeeded > 0 
                                    ? `SELECT ${moviesNeeded} MORE MOVIE${moviesNeeded > 1 ? 'S' : ''} TO START.` 
                                    : "YOU'RE READY TO INITIATE DISCOVERY."}
                            </motion.p>
                        </AnimatePresence>
                    </div>
                    <ModalCloseButton onClick={onClose} className="hover:rotate-90 transition-transform duration-500 scale-125" />
                </header>

                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1, duration: 0.8 }}
                    className="space-y-10"
                >
                    <section className="space-y-4">
                        <h3 className="text-[10px] font-black uppercase tracking-[0.4em] text-primary/80 flex items-center gap-4">
                            <span className="opacity-30 italic">01.</span> PREFERRED GENRES
                            <div className="h-[1px] flex-grow bg-white/5" />
                        </h3>
                        <GenreSelector />
                    </section>

                    <section className="space-y-4">
                        <h3 className="text-[10px] font-black uppercase tracking-[0.4em] text-primary/80 flex items-center gap-4">
                            <span className="opacity-30 italic">02.</span> SEED MOVIES
                            <div className="h-[1px] flex-grow bg-white/5" />
                        </h3>
                        <MovieAutocomplete />
                        <SelectedMovies />
                    </section>

                    <footer className="pt-4">
                        <RecommendCTA onDone={onClose} />
                    </footer>
                </motion.div>
            </div>
        </Modal>
    )
}
