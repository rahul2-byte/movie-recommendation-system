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

  return (
    <header className="sticky top-0 z-50 border-b border-line/80 bg-ink/95 backdrop-blur">
      <nav
        aria-label="Primary"
        className="relative mx-auto flex h-[68px] w-full max-w-[1440px] items-center px-4 sm:px-6 lg:px-10"
      >
        <Link
          href="/"
          className="text-lg font-extrabold tracking-[-0.04em] text-paper"
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
              className={`border-b-2 py-[23px] text-sm font-semibold transition-colors ${
                pathname === link.href
                  ? "border-crimson text-paper"
                  : "border-transparent text-muted hover:text-paper"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <Link
            href="/search"
            className="grid size-10 place-items-center text-muted transition-colors hover:text-paper"
            aria-label="Search movies"
          >
            <Search className="h-5 w-5" />
          </Link>
          <Link
            href="/#build-lineup"
            className="hidden min-h-10 items-center bg-crimson px-4 text-sm font-bold text-white transition-colors hover:bg-crimson-bright sm:inline-flex"
          >
            Build lineup
          </Link>
          <button
            type="button"
            className="grid size-10 place-items-center text-muted transition-colors hover:text-paper md:hidden"
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
            className="absolute inset-x-0 top-full border-b border-line bg-ink p-4 shadow-2xl md:hidden"
          >
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="block border-b border-line py-3 text-sm font-semibold text-muted transition-colors hover:text-paper"
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/#build-lineup"
              onClick={() => setOpen(false)}
              className="mt-3 inline-flex bg-crimson px-4 py-3 text-sm font-bold text-white"
            >
              Build lineup
            </Link>
          </div>
        )}
      </nav>
    </header>
  )
}
