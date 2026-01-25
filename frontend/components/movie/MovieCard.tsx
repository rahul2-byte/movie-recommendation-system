import Image from "next/image"

export function MovieCard({ movie }) {
  return (
    <div className="w-[160px] shrink-0 space-y-2">
      <div className="relative aspect-[2/3] rounded-lg overflow-hidden bg-neutral-800">
        {movie.posterUrl ? (
          <Image
            src={movie.posterUrl}
            alt={movie.title}
            fill
            className="object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-sm text-neutral-400">
            Poster Unavailable
          </div>
        )}
      </div>

      <div>
        <p className="font-semibold leading-tight truncate">
          {movie.title}
        </p>
        <p className="text-sm text-neutral-500 font-medium">
          {movie.year} · ⭐ {movie.rating?.toFixed(1) ?? "—"}
        </p>
      </div>
    </div>
  )
}
