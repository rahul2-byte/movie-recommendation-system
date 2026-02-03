"use client"

import { Modal } from "@/shared/ui/Modal"
import { RecommendedMovie } from "@/features/recommendations/types"
import Image from "next/image"
import { Button } from "@/shared/ui/Button"
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
    <Modal className="z-[200]">
      <div className="relative max-w-4xl w-full bg-[#0a0f1d] text-white rounded-[2rem] overflow-hidden border border-white/10 shadow-2xl">
        <div className="absolute top-4 right-4 z-50">
            <ModalCloseButton onClick={onClose} />
        </div>
        
        <div className="grid md:grid-cols-[2fr_3fr] h-full max-h-[85vh] overflow-y-auto md:overflow-hidden">
            {/* Image Section */}
            <div className="relative aspect-[2/3] md:h-full bg-black/50 min-h-[300px]">
                {movie.posterUrl ? (
                    <Image
                        src={movie.posterUrl}
                        alt={movie.title}
                        fill
                        className="object-cover"
                        sizes="(max-width: 768px) 100vw, 400px"
                    />
                ) : (
                    <div className="absolute inset-0 flex items-center justify-center text-white/20 font-bold uppercase tracking-widest">
                        No Poster
                    </div>
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-[#0a0f1d] via-transparent to-transparent md:bg-gradient-to-r md:from-transparent md:to-[#0a0f1d]" />
            </div>

            {/* Content Section */}
            <div className="p-8 md:p-12 space-y-8 flex flex-col justify-center h-full overflow-y-auto">
                <div className="space-y-3">
                    <h2 className="text-3xl md:text-5xl font-black uppercase italic tracking-tighter leading-[0.9] text-white">
                        {movie.title}
                    </h2>
                    <div className="flex flex-wrap gap-6 text-[11px] font-bold uppercase tracking-[0.2em] text-white/50">
                        {movie.year && (
                            <span className="flex items-center gap-2">
                                <Calendar className="w-3 h-3" /> {movie.year}
                            </span>
                        )}
                        {movie.score && (
                            <span className="flex items-center gap-2 text-primary">
                                <Star className="w-3 h-3 fill-current" /> {Math.round(movie.score * 100)}% Match
                            </span>
                        )}
                    </div>
                </div>

                <div className="flex flex-wrap gap-2">
                    {movie.genres.map(genre => (
                        <span key={genre} className="px-3 py-1 bg-white/5 border border-white/5 rounded-full text-[10px] font-bold uppercase tracking-wider text-white/70">
                            {genre}
                        </span>
                    ))}
                </div>

                <div className="space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-widest text-primary/80 flex items-center gap-2">
                        <Info className="w-3 h-3" /> Synopsis
                    </h3>
                    <p className="text-sm md:text-base leading-relaxed text-white/70 font-medium">
                        {movie.overview || "No synopsis available for this title."}
                    </p>
                </div>
            </div>
        </div>
      </div>
    </Modal>
  )
}
