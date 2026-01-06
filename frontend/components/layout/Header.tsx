/**
 * Header Component
 * 
 * Sticky navigation bar that appears at the top of every page.
 * Features:
 * - Brand logo/name with link to home
 * - Navigation links
 * - Active link highlighting
 * - Mobile responsive (TODO: add mobile menu)
 * 
 */

"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

// Navigation items configuration
// Centralized so we can easily add/remove items
const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/my-list", label: "My List" },
  { href: "/project", label: "Project" },
  { href: "/about", label: "About" },
] as const

export function Header() {
  // Get current pathname to highlight active link
  const pathname = usePathname()

  return (
    <header
      className="sticky top-0 z-50 bg-[var(--color-bg-base)] backdrop-blur border-b border-[var(--color-bg-muted)]"
      role="banner"
    >
      <div className="mx-auto max-w-[1400px] px-6 h-16 flex items-center justify-between">

        {/* Brand Logo - Links to home page */}
        <Link
          href="/"
          className="text-xl font-semibold tracking-tight hover:text-[var(--color-accent-teal)] transition-colors"
          aria-label="Movies99 home"
        >
          Movies99 {/* ✅ Fixed: was Movies99 */}
        </Link>

        {/* Main Navigation */}
        <nav className="flex items-center gap-6 text-sm" role="navigation" aria-label="Main navigation">
          {NAV_ITEMS.map((item) => {
            // Check if this is the active page
            const isActive = pathname === item.href

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`
                  hover:text-[var(--color-accent-teal)] 
                  transition-colors
                  ${isActive ? 'text-[var(--color-accent-teal)] font-semibold border-b-2 border-[var(--color-accent-teal)]' : ''}
                `}
                aria-current={isActive ? "page" : undefined}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}