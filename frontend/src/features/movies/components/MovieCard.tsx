"use client"

import Image from "next/image"
import { Card, CardContent } from "@/shared/ui/Card"
import type { Movie } from "@/features/movies/types/movie"
import { motion } from "framer-motion"

interface MovieCardProps {
  movie: Movie
  index?: number
}

export function MovieCard({ movie, index = 0 }: MovieCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      whileHover={{ y: -12, transition: { duration: 0.3 } }}
      className="group"
    >
      <Card className="w-[220px] shrink-0 overflow-hidden border border-white/5 bg-card transition-all group-hover:border-primary/30 card-shadow-hover rounded-[1.5rem]">
        <div className="relative aspect-[2/3] overflow-hidden bg-muted">
          {movie.posterUrl ? (
            <Image
              src={movie.posterUrl}
              alt={movie.title}
              fill
              className="object-cover transition-transform duration-700 group-hover:scale-110"
              sizes="220px"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-[10px] text-muted-foreground uppercase font-bold tracking-widest text-center px-4">
              Poster Unavailable
            </div>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-background/90 via-transparent to-transparent opacity-60 transition-opacity group-hover:opacity-100" />
        </div>
        <CardContent className="p-5 relative">
          <h3 className="text-sm font-bold leading-snug truncate text-foreground group-hover:text-primary transition-colors mb-1">
            {movie.title}
          </h3>
          <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-[0.1em] text-muted-foreground/50">
            <span>{movie.year}</span>
            <div className="flex items-center gap-1.5">
              <span className="text-primary">★</span>
              <span className="text-foreground/70">{movie.rating?.toFixed(1) ?? "—"}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
