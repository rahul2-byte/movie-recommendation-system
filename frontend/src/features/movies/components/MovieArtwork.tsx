"use client"

import Image from "next/image"
import { useState } from "react"

type MovieArtworkProps = {
  title: string
  posterUrl?: string | null
  backdropUrl?: string | null
  variant?: "poster" | "backdrop"
  priority?: boolean
  sizes: string
  alt?: string
  showFallbackLabel?: boolean
}

export function MovieArtwork({
  title,
  posterUrl,
  backdropUrl,
  variant = "poster",
  priority = false,
  sizes,
  alt = title,
  showFallbackLabel = true,
}: MovieArtworkProps) {
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)
  const src = variant === "backdrop" ? backdropUrl || posterUrl : posterUrl

  return (
    <div
      className={`absolute inset-0 overflow-hidden bg-panel ${
        loaded ? "bg-ink" : "animate-pulse"
      }`}
    >
      {src && !failed ? (
        <Image
          src={src}
          alt={alt}
          fill
          className={`object-cover transition-[opacity,transform] duration-300 ${
            loaded ? "opacity-100" : "opacity-0"
          }`}
          sizes={sizes}
          priority={priority}
          quality={variant === "backdrop" ? 70 : 75}
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="grid h-full place-content-center justify-items-center gap-2 p-4 text-center text-dim">
          {showFallbackLabel && (
            <>
              <span className="font-bold tracking-[0.12em] text-crimson">
                M99
              </span>
              <small className="text-[0.65rem] uppercase tracking-[0.14em]">
                Artwork unavailable
              </small>
            </>
          )}
        </div>
      )}
    </div>
  )
}
