import Link from "next/link"

export function Header() {
  return (
    <header className="fixed top-0 z-50 w-full bg-black/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-8">
        <Link href="/" className="text-xl font-bold text-pink-500">
          CineSeek
        </Link>

        <nav className="flex gap-8 text-sm text-gray-300">
          <Link href="/">Home</Link>
          <Link href="/recommendations">My List</Link>
          <Link href="/project">Project</Link>
          <Link href="/about">About</Link>
        </nav>
      </div>
    </header>
  )
}
