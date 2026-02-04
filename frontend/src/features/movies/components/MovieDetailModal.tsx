"use client"

import { Modal } from "@/shared/ui/Modal"
import { RecommendedMovie } from "@/features/recommendations/types"
import Image from "next/image"
import { Star, Calendar, Info } from "lucide-react"
import { ModalCloseButton } from "@/shared/ui/ModalCloseButton"

export function MovieDetailModal({
  movie,
  isOpen,
  onClose,
}: {
  movie: RecommendedMovie | null
  isOpen: boolean
  onClose: () => void
}) {
  if (!movie || !isOpen) return null

  return (
    <Modal contentClassName="p-0">
      <div className="relative w-full bg-surface-strong text-foreground rounded-xl overflow-hidden border border-border/60 shadow-hero">
        <div className="absolute top-4 right-4 z-50">
          <ModalCloseButton onClick={onClose} />
        </div>

        <div className="grid md:grid-cols-5 h-full max-h-modal overflow-y-auto md:overflow-hidden">
          <div className="relative aspect-poster md:h-full bg-surface md:col-span-2">
            {movie.posterUrl ? (
              <Image
                src={movie.posterUrl}
                alt={movie.title}
                fill
                className="object-cover"
                sizes="(max-width: 768px) 100vw, 400px"
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center text-overline text-muted-foreground">
                No Poster
              </div>
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-surface-strong via-transparent to-transparent md:bg-gradient-to-r md:from-transparent md:to-surface-strong" />
          </div>

          <div className="p-card space-y-stack flex flex-col justify-center h-full overflow-y-auto md:col-span-3">
            <div className="space-y-tight">
              <h2 className="text-h1 font-semibold leading-h1">
                {movie.title}
              </h2>
              <div className="flex flex-wrap gap-6 text-overline text-muted-foreground/80">
                {movie.year && (
                  <span className="flex items-center gap-2">
                    <Calendar className="w-3 h-3" /> {movie.year}
                  </span>
                )}
                {movie.score && (
                  <span className="flex items-center gap-2 text-primary">
                    <Star className="w-3 h-3 fill-current" />
                    {Math.round(movie.score * 100)}% Match
                  </span>
                )}
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {movie.genres.map((genre) => (
                <span
                  key={genre}
                  className="px-chip py-tight bg-surface border border-border rounded-pill text-overline text-muted-foreground"
                >
                  {genre}
                </span>
              ))}
            </div>

            <div className="space-y-tight">
              <h3 className="text-overline text-primary/80 flex items-center gap-2">
                <Info className="w-3 h-3" /> Synopsis
              </h3>
              <p className="text-body text-muted-foreground">
                {movie.overview || "No synopsis available for this title."}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  )
}
