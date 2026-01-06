import Link from "next/link"

export function Footer() {
  return (
    <footer
      className="border-t"
      style={{
        backgroundColor: "var(--color-bg-subtle)",
        borderColor: "var(--color-bg-muted)",
      }}
    >
      {/* Main footer content */}
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="grid grid-cols-3 gap-5 md:grid-cols-3">
          
          {/* Column 1 — Brand */}
          <div>
            <h3
              className="mb-3 text-lg font-semibold"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Movies99
            </h3>
            <p className="max-w-xs text-sm text-[var(--color-text-secondary)]">
              ML-powered movie recommendations using MovieLens, FAISS, and modern ranking models.
            </p>
          </div>

          {/* Column 2 — Navigation */}
          <div>
            <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-primary)]">
              Explore
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]">
                  Home
                </Link>
              </li>
              <li>
                <Link href="/recommendations" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]">
                  Recommendations
                </Link>
              </li>
              <li>
                <Link href="/project" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]">
                  System Design
                </Link>
              </li>
              <li>
                <Link href="/about" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]">
                  About
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 3 — Meta / Social */}
          <div>
            <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-primary)]">
              Connect
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a href="#" className="text-[var(--color-text-secondary)] hover:text-[var(--color-accent-teal)]">
                  GitHub
                </a>
              </li>
              <li>
                <a href="#" className="text-[var(--color-text-secondary)] hover:text-[var(--color-accent-teal)]">
                  LinkedIn
                </a>
              </li>
              <li>
                <a href="#" className="text-[var(--color-text-secondary)] hover:text-[var(--color-accent-teal)]">
                  Twitter / X
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div
        className="border-t py-4"
        style={{ borderColor: "var(--color-bg-muted)" }}
      >
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-6 text-xs text-[var(--color-text-muted)] md:flex-row">
          <span>© {new Date().getFullYear()} Movies99</span>

          <div className="flex gap-4">
            <span className="hover:text-[var(--color-text-primary)] cursor-pointer">
              Privacy
            </span>
            <span className="hover:text-[var(--color-text-primary)] cursor-pointer">
              Terms
            </span>
            <span className="hover:text-[var(--color-text-primary)] cursor-pointer">
              Cookies
            </span>
          </div>
        </div>
      </div>
    </footer>
  )
}
