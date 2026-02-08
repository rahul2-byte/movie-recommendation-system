"use client"

import { Modal } from "@/shared/ui/Modal"
import { Movie } from "@/features/movies/types/movie"
import Image from "next/image"
import { Star, Info, X, RotateCcw } from "lucide-react"
import { useMovieDetail } from "../hooks/useMovieDetail"
import { formatMovieTitle } from "@/shared/lib/utils"

export function MovieDetailModal({
  movieId,
  tmdbId,
  isOpen,
  onClose,
}: {
  movieId: number | null
  tmdbId?: number | null
  isOpen: boolean
  onClose: () => void
}) {
  const { data: movie, isLoading, isError, refetch } = useMovieDetail(movieId, tmdbId)

  if (!isOpen) return null

  // Loading State
  if (isLoading) {
    return (
      <Modal contentClassName="p-0 max-w-5xl max-h-[90vh] overflow-hidden bg-background border border-border/60 shadow-2xl rounded-2xl">
        <div className="relative w-full h-full min-h-[500px] flex flex-col">
           <div className="w-full aspect-video bg-surface-strong animate-pulse shrink-0" />
           <div className="p-8 space-y-4 grow">
              <div className="h-8 bg-surface-strong rounded w-1/3 animate-pulse" />
              <div className="h-4 bg-surface-strong rounded w-full animate-pulse" />
              <div className="h-4 bg-surface-strong rounded w-2/3 animate-pulse" />
           </div>
           <button
            className="absolute top-4 right-4 z-50 p-2 rounded-full bg-black/40 text-white hover:bg-black/60 transition-colors"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-6 w-6" />
          </button>
        </div>
      </Modal>
    )
  }

  // Error State or Movie Not Found
  if (isError || !movie) {
    return (
      <Modal contentClassName="p-0 max-w-5xl max-h-screen">
        <div className="relative w-full h-[50vh] bg-surface-strong text-foreground rounded-xl overflow-hidden border border-border/60 shadow-hero flex flex-col items-center justify-center p-card">
          <button
            className="absolute top-4 right-4 z-50 p-2 rounded-full bg-surface-strong/80 hover:bg-surface-strong text-muted-foreground hover:text-foreground transition-colors"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-6 w-6" />
          </button>
          <div className="flex flex-col items-center gap-4 text-center">
             <p className="text-h3 text-destructive">Failed to load movie details.</p>
             <button 
                onClick={() => refetch()} 
                className="flex items-center gap-2 px-6 py-3 bg-surface hover:bg-surface-soft border border-border rounded-full transition-all text-muted-foreground hover:text-foreground hover:border-primary/50"
             >
                <RotateCcw className="w-4 h-4" /> 
                <span className="text-body font-medium">Try Again</span>
             </button>
          </div>
        </div>
      </Modal>
    )
  }

  const formattedTitle = formatMovieTitle(movie.title);
  
  return (
    <Modal contentClassName="p-0 max-w-5xl max-h-[90vh] overflow-hidden bg-background border border-border/60 shadow-2xl rounded-2xl">
      <div className="relative h-full flex flex-col overflow-y-auto no-scrollbar">
        
        {/* 1. Cinematic Hero Section */}
        <div className="relative w-full aspect-video md:aspect-[2.4/1] bg-surface-strong shrink-0">
           {/* Image */}
           <Image 
             src={movie.backdropUrl || movie.posterUrl || ""} 
             alt={formattedTitle}
             fill
             className="object-cover object-top"
             priority
           />
           
           {/* Gradient Overlay (The "Netflix" fade) */}
           <div className="absolute inset-0 bg-gradient-to-t from-background via-background/60 to-transparent" />

           {/* Content Overlay (Title, Match Score) */}
           <div className="absolute bottom-0 left-0 w-full p-6 md:p-10 z-10 space-y-4">
              <h2 className="text-hero font-serif leading-none text-white drop-shadow-lg max-w-3xl">
                {formattedTitle}
              </h2>
              
              <div className="flex items-center gap-4 text-sm font-medium flex-wrap">
                 {movie.score && (
                   <span className="text-green-400 font-bold px-2 py-1 bg-green-400/10 rounded border border-green-400/20 backdrop-blur-md">
                     {Math.round(movie.score * 100)}% Match
                   </span>
                 )}
                 <span className="text-white/80">{movie.year}</span>
                 {movie.runtime && <span className="text-white/80">{movie.runtime} min</span>}
                 {movie.voteAverage && (
                   <span className="flex items-center gap-1 text-amber-400">
                      <Star className="w-4 h-4 fill-current" /> {movie.voteAverage.toFixed(1)}
                   </span>
                 )}
              </div>
           </div>
           
           {/* Close Button (Floating) */}
           <button 
             onClick={onClose}
             className="absolute top-4 right-4 p-2 bg-black/40 hover:bg-black/60 backdrop-blur-md rounded-full text-white transition-all z-20"
           >
              <X className="w-6 h-6" />
           </button>
        </div>

        {/* 2. Content Grid */}
        <div className="grid md:grid-cols-[2fr_1fr] gap-8 p-6 md:p-10">
          
          {/* Left Col: Synopsis & Genes */}
          <div className="space-y-6">
             {/* Explainability Badge */}
             {movie.retrieval_sources && movie.retrieval_sources.length > 0 && (
               <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-medium">
                 <Info className="w-3 h-3" />
                 Recommended because: {movie.retrieval_sources.map(s => s.replace(/_/g, " ")).join(", ")}
               </div>
             )}

             <div className="space-y-2">
               <h3 className="text-lg font-semibold text-foreground">Synopsis</h3>
               <p className="text-muted-foreground leading-relaxed">
                 {movie.overview || "No synopsis available."}
               </p>
             </div>

             <div className="space-y-2">
               <h3 className="text-sm font-semibold text-foreground/70 uppercase tracking-wider">Genres</h3>
               <div className="flex flex-wrap gap-2">
                 {movie.genres.map(g => (
                   <span key={g} className="px-3 py-1 bg-surface border border-border rounded-full text-xs text-muted-foreground hover:text-foreground transition-colors cursor-default">
                     {g}
                   </span>
                 ))}
               </div>
             </div>
          </div>

          {/* Right Col: Cast & Details */}
          <div className="space-y-6 text-sm">
             {movie.cast && movie.cast.length > 0 && (
                <div className="space-y-1">
                 <span className="block text-muted-foreground/60 text-xs uppercase">Cast</span>
                 <p className="text-foreground/90">
                   {movie.cast.slice(0, 5).join(", ")}
                 </p>
               </div>
             )}
             
             {movie.director && (
                <div className="space-y-1">
                 <span className="block text-muted-foreground/60 text-xs uppercase">Director</span>
                 <p className="text-foreground/90">{movie.director}</p>
               </div>
             )}

             {movie.tagline && (
                <div className="space-y-1">
                 <span className="block text-muted-foreground/60 text-xs uppercase">Tagline</span>
                 <p className="italic text-muted-foreground">"{movie.tagline}"</p>
               </div>
             )}
          </div>
        </div>
      </div>
    </Modal>
  )
}
