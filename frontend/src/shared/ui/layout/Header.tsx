"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useState } from "react"
import { Menu, Search, X } from "lucide-react"

const links = [
  { href: "/", label: "Discover" },
  { href: "/catalog", label: "Browse" },
  { href: "/about", label: "About" },
]

export function Header() {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)
  const isHome = pathname === "/"

  return (
    <header
      className={
        isHome
          ? "absolute inset-x-0 top-0 z-50 bg-gradient-to-b from-ink/70 to-transparent text-white"
          : "sticky top-0 z-50 border-b border-line/80 bg-canvas/90 backdrop-blur-xl"
      }
    >
      <Link
        href="#main-content"
        className="fixed left-4 top-3 z-[70] -translate-y-20 rounded-full bg-ink px-4 py-2 text-sm font-bold text-white transition-transform focus:translate-y-0"
      >
        Skip to content
      </Link>
      <nav
        aria-label="Primary"
        className="relative mx-auto flex h-[72px] w-full max-w-[1440px] items-center px-4 sm:px-6 lg:px-10"
      >
        <Link
          href="/"
          className={`focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson text-xl font-extrabold tracking-[-0.06em] ${isHome ? "text-white" : "text-paper"}`}
          aria-label="M99 home"
        >
          <span className="text-crimson">M</span>99
        </Link>

        <div className="ml-8 mr-auto hidden items-center gap-7 md:flex">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={pathname === link.href ? "page" : undefined}
              className={`focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson relative py-[25px] text-sm font-semibold transition-colors after:absolute after:inset-x-0 after:bottom-4 after:h-0.5 after:origin-left after:transition-transform ${
                pathname === link.href
                  ? `${isHome ? "text-white" : "text-paper"} after:scale-x-100 after:bg-crimson`
                  : `${isHome ? "text-white/70 hover:text-white" : "text-muted hover:text-paper"} after:scale-x-0 after:bg-crimson hover:after:scale-x-100`
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <Link
            href="/search"
            className={`focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson grid size-10 place-items-center rounded-full transition-colors ${isHome ? "text-white/80 hover:bg-white/10 hover:text-white" : "text-muted hover:bg-panel hover:text-paper"}`}
            aria-label="Search movies"
          >
            <Search className="h-5 w-5" />
          </Link>
          <Link
            href="/#build-lineup"
            className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson hidden min-h-10 items-center rounded-full bg-crimson px-5 text-sm font-bold text-white transition-colors hover:bg-crimson-bright active:scale-[0.98] sm:inline-flex"
          >
            Build lineup
          </Link>
          <button
            type="button"
            className={`focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson grid size-10 place-items-center rounded-full transition-colors md:hidden ${isHome ? "text-white/80 hover:bg-white/10 hover:text-white" : "text-muted hover:bg-panel hover:text-paper"}`}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            aria-controls="mobile-navigation"
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {open && (
          <div
            id="mobile-navigation"
            className={`absolute inset-x-0 top-full border-b p-4 shadow-[0_24px_60px_rgba(25,25,28,0.12)] md:hidden ${isHome ? "border-white/10 bg-ink/95" : "border-line bg-panel"}`}
          >
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className={`focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson block border-b py-3 text-sm font-semibold transition-colors ${isHome ? "border-white/10 text-white/70 hover:text-white" : "border-line text-muted hover:text-paper"}`}
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/#build-lineup"
              onClick={() => setOpen(false)}
              className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson mt-3 inline-flex rounded-full bg-crimson px-5 py-3 text-sm font-bold text-white"
            >
              Build lineup
            </Link>
          </div>
        )}
      </nav>
    </header>
  )
}
