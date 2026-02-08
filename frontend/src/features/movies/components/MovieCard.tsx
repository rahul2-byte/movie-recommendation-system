"use client"

import Image from "next/image"
import type { Movie } from "@/features/movies/types/movie"
import { LazyMotion, domAnimation, m } from "framer-motion"

interface MovieCardProps {
  movie: Movie
  index?: number
  onClick?: () => void
  selected?: boolean
}

export function MovieCard({ movie, index = 0, onClick, selected = false }: MovieCardProps) {
  return (
    <LazyMotion features={domAnimation} strict>
      <m.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.05 }}
        className={`movie-card group ${selected ? "movie-card-selected" : ""}`}
        onClick={onClick}
      >
        <div 
          className="relative aspect-[2/3] w-full overflow-hidden rounded-md bg-[rgba(255,255,255,0.03)]"
          aria-label={`View details for ${movie.title}`}
          role="button"
        >
          {movie.posterUrl ? (
            <Image
              src={movie.posterUrl}
              alt={movie.title}
              fill
              className="movie-card-poster transition-transform duration-500 group-hover:scale-110"
              sizes="(max-width: 640px) 50vw, (max-width: 1024px) 25vw, (max-width: 1280px) 20vw, 15vw"
              priority={index < 4}
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-xs text-text-muted uppercase tracking-widest border border-white/10 rounded-md">
              No Poster
            </div>
          )}
          
          {/* Hover Overlay with Gradient */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-4">
            <h3 className="text-lg font-serif text-white capitalize leading-tight mb-1 drop-shadow-md transform translate-y-2 group-hover:translate-y-0 transition-transform duration-300">
              {movie.title}
            </h3>
            <div className="flex items-center gap-2 text-xs text-gray-300 transform translate-y-2 group-hover:translate-y-0 transition-transform duration-300 delay-75">
              <span>{movie.year}</span>
              <span>•</span>
              <span className="flex items-center gap-1 text-accent">
                <span>★</span>
                <span>{movie.rating?.toFixed(1) ?? "—"}</span>
              </span>
            </div>
          </div>

          {selected && (
            <div className="movie-card-checkmark z-10">
              ✓
            </div>
          )}
        </div>
      </m.div>
    </LazyMotion>
  )
}
