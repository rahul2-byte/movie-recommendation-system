import Link from "next/link"

export function Footer() {
  return (
    <footer className="border-t border-line bg-ink py-12">
      <div className="mx-auto grid w-full max-w-[1440px] gap-10 px-4 sm:grid-cols-2 sm:px-6 lg:grid-cols-[1.4fr_0.7fr_0.7fr] lg:px-10">
        <div>
          <Link
            href="/"
            className="text-lg font-extrabold tracking-[-0.04em] text-paper"
            aria-label="M99 home"
          >
            <span className="text-crimson">M</span>99
          </Link>
          <p className="mt-4 max-w-xs text-sm leading-6 text-muted">
            Find what to watch next, starting with what you already love.
          </p>
        </div>
        <div className="flex flex-col gap-3 text-sm">
          <strong className="text-xs font-bold uppercase tracking-[0.14em] text-paper">
            Explore
          </strong>
          <Link className="text-muted hover:text-paper" href="/">
            Discover
          </Link>
          <Link className="text-muted hover:text-paper" href="/catalog">
            Browse
          </Link>
          <Link className="text-muted hover:text-paper" href="/about">
            About the engine
          </Link>
        </div>
        <div className="flex flex-col gap-3 text-sm">
          <strong className="text-xs font-bold uppercase tracking-[0.14em] text-paper">
            Project
          </strong>
          <a
            href="https://github.com/rahul2-byte/movie-recommendation-system"
            target="_blank"
            rel="noreferrer"
            className="text-muted hover:text-paper"
          >
            GitHub repository
          </a>
          <a
            href="https://www.linkedin.com/in/-rahul-singh22/"
            target="_blank"
            rel="noreferrer"
            className="text-muted hover:text-paper"
          >
            Developer
          </a>
        </div>
      </div>
      <div className="mx-auto mt-10 flex w-full max-w-[1440px] flex-col gap-2 border-t border-line pt-5 text-xs text-dim sm:flex-row sm:justify-between sm:px-6 lg:px-10">
        <span>© {new Date().getFullYear()} M99</span>
        <span>Movie data from TMDB · Training data from MovieLens</span>
      </div>
    </footer>
  )
}
