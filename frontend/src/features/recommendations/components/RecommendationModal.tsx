"use client"

import { GenreSelector } from "./GenreSelector"
import { MovieAutocomplete } from "./MovieAutocomplete"
import { SelectedMovies } from "./SelectedMovies"
import { RecommendCTA } from "./RecommendCTA"
import { Modal } from "@/shared/ui/Modal"
import { ModalCloseButton } from "@/shared/ui/ModalCloseButton"
import { motion } from "framer-motion"

export function RecommendationModal({
    onClose,
}: {
    onClose: () => void
}) {
    return (
        <Modal>
            <div className="flex flex-col space-y-12">
                <header className="flex items-start justify-between">
                    <div className="space-y-2">
                        <h2 className="text-4xl font-bold tracking-tighter text-white uppercase italic">
                            Define Your <span className="text-primary">Taste</span>
                        </h2>
                        <p className="text-muted-foreground/60 text-sm font-medium uppercase tracking-widest">
                            Pick genres or search for movies you love.
                        </p>
                    </div>
                    <ModalCloseButton onClick={onClose} className="hover:rotate-90 transition-transform duration-300" />
                </header>

                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="space-y-12"
                >
                    <section className="space-y-4">
                        <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-primary">01. Preferred Genres</h3>
                        <GenreSelector />
                    </section>

                    <section className="space-y-4">
                        <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-primary">02. Seed Movies</h3>
                        <MovieAutocomplete />
                        <SelectedMovies />
                    </section>

                    <footer className="pt-6">
                        <RecommendCTA onDone={onClose} />
                    </footer>
                </motion.div>
            </div>
        </Modal>
    )
}