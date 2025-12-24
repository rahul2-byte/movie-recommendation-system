"use client"

import { motion } from "framer-motion"
import Link from "next/link"
import { Movie } from "@/lib/types/movie"

interface Props {
  movie: Movie
}

export function MovieCard({ movie }: Props) {
  return (
    <Link href={`/movie/${movie.movieId}`}>
      <motion.div
        whileHover={{ scale: 1.05 }}
        className="relative w-44 shrink-0 cursor-pointer"
      >
        <img
          src={movie.posterUrl}
          alt={movie.title}
          className="rounded-lg object-cover"
        />

        <div className="absolute inset-0 rounded-lg bg-gradient-to-t
          from-black/80 via-black/20 to-transparent
          opacity-0 hover:opacity-100 transition"
        >
          <div className="absolute bottom-3 left-3 right-3 text-sm">
            <p className="font-semibold">{movie.title}</p>
            <p className="text-xs text-gray-300">
              {movie.year} • ⭐ {movie.rating}
            </p>
          </div>
        </div>
      </motion.div>
    </Link>
  )
}
