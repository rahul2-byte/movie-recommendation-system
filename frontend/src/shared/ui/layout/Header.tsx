"use client"

import Link from "next/link"

export function Header() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-transparent px-8 py-6">
      <Link
        href="/"
        className="font-serif text-xl font-normal text-white no-underline tracking-wide"
      >
        <span className="text-accent">M99</span>
      </Link>
    </nav>
  )
}
