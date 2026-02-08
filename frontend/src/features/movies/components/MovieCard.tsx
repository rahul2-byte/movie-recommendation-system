"use client"

import Image from "next/image"
import { Card, CardContent } from "@/shared/ui/Card"
import type { Movie } from "@/features/movies/types/movie"
import { LazyMotion, domAnimation, m } from "framer-motion"

interface MovieCardProps {
  movie: Movie
  index?: number
  onClick?: () => void
}

export function MovieCard({ movie, index = 0, onClick }: MovieCardProps) {
  return (
    <LazyMotion features={domAnimation} strict>
      <m.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.04 }}
        whileHover={{ y: -8, transition: { duration: 0.25 } }}
        className="group w-full cursor-pointer"
        onClick={onClick}
      >
        <Card className="w-full h-full overflow-hidden border-border/60 bg-surface-strong transition-all group-hover:border-primary/40">
          <div className="relative aspect-poster w-full overflow-hidden bg-surface">
            {movie.posterUrl ? (
              <Image
                src={movie.posterUrl}
                alt={movie.title}
                fill
                className="object-cover transition-transform duration-700 group-hover:scale-105"
                sizes="(max-width: 640px) 50vw, (max-width: 768px) 33vw, (max-width: 1024px) 25vw, 20vw"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-overline text-muted-foreground text-center px-card">
                Poster Unavailable
              </div>
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-background/90 via-transparent to-transparent opacity-60 transition-opacity group-hover:opacity-90" />
          </div>
          <CardContent className="p-card relative">
            <h3 className="text-body font-semibold leading-h3 truncate text-foreground group-hover:text-primary transition-colors">
              {movie.title}
            </h3>
            <div className="mt-tight flex items-center justify-between text-caption text-muted-foreground">
              <span>{movie.year}</span>
              <div className="flex items-center gap-2">
                <span className="text-primary">★</span>
                <span className="text-foreground/70">
                  {movie.rating?.toFixed(1) ?? "—"}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </m.div>
    </LazyMotion>
  )
}
