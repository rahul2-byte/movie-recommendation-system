import Link from "next/link"

export function Footer() {
  return (
    <footer className="py-12 border-t border-[rgba(255,255,255,0.1)] mt-20 bg-black relative z-10">
      <div className="container flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="text-center md:text-left">
          <span className="font-serif text-xl text-white block mb-2">M99</span>
          <p className="text-sm text-text-muted">
            © {new Date().getFullYear()} Zeek. All rights reserved.
          </p>
        </div>

        <div className="flex items-center gap-8">
          <Link 
            href="https://github.com" 
            target="_blank" 
            className="text-sm text-text-muted hover:text-accent transition-colors uppercase tracking-wider"
          >
            GitHub
          </Link>
          <Link 
            href="https://linkedin.com" 
            target="_blank" 
            className="text-sm text-text-muted hover:text-accent transition-colors uppercase tracking-wider"
          >
            LinkedIn
          </Link>
          <Link 
            href="#" 
            target="_blank" 
            className="text-sm text-text-muted hover:text-accent transition-colors uppercase tracking-wider"
          >
            Portfolio
          </Link>
        </div>
      </div>
    </footer>
  )
}
