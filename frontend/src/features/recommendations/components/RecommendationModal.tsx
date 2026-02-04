"use client"

import { GenreSelector } from "./GenreSelector"
import { MovieAutocomplete } from "./MovieAutocomplete"
import { SelectedMovies } from "./SelectedMovies"
import { RecommendCTA } from "./RecommendCTA"
import { Modal } from "@/shared/ui/Modal"
import { ModalCloseButton } from "@/shared/ui/ModalCloseButton"
import { LazyMotion, domAnimation, m, AnimatePresence } from "framer-motion"
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
      <div className="flex flex-col space-y-stack">
        <header className="flex items-start justify-between">
          <div className="space-y-tight">
            <h2 className="text-h2 font-semibold">
              Define your <span className="text-primary">taste</span>
            </h2>

            <AnimatePresence mode="wait">
              <m.p
                key={moviesNeeded}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                className="text-overline text-muted-foreground"
              >
                {moviesNeeded > 0
                  ? `Select ${moviesNeeded} more movie${
                      moviesNeeded > 1 ? "s" : ""
                    } to start.`
                  : "You are ready to begin discovery."}
              </m.p>
            </AnimatePresence>
          </div>
          <ModalCloseButton onClick={onClose} className="hover:rotate-90 transition-transform duration-500" />
        </header>

        <LazyMotion features={domAnimation} strict>
          <m.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05, duration: 0.6 }}
            className="space-y-stack"
          >
            <section className="space-y-tight">
              <h3 className="text-overline text-primary/80 flex items-center gap-4">
                <span className="opacity-40">01</span>
                Preferred genres
                <div className="h-px flex-grow bg-border/60" />
              </h3>
              <GenreSelector />
            </section>

            <section className="space-y-tight">
              <h3 className="text-overline text-primary/80 flex items-center gap-4">
                <span className="opacity-40">02</span>
                Seed movies
                <div className="h-px flex-grow bg-border/60" />
              </h3>
              <MovieAutocomplete />
              <SelectedMovies />
            </section>

            <footer className="pt-tight">
              <RecommendCTA onDone={onClose} />
            </footer>
          </m.div>
        </LazyMotion>
      </div>
    </Modal>
  )
}
