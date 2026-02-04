import { siteConfig } from "@/shared/config/site"

export function Footer() {
  return (
    <footer className="w-full mt-section pb-section">
      <div className="h-px w-full bg-gradient-to-r from-transparent via-border to-transparent" />

      <div className="container flex flex-col md:flex-row justify-between items-center gap-stack pt-stack">
        <div className="space-y-tight text-center md:text-left">
          <span className="text-h3 font-semibold italic tracking-tight text-primary uppercase">
            {siteConfig.shortName}
          </span>
          <p className="text-overline text-muted-foreground/60">
            © 2026 Cinematic Intelligence
          </p>
        </div>

        <nav className="flex flex-wrap items-center justify-center gap-6 text-overline text-muted-foreground/70">
          {siteConfig.footerLinks.map((item) => (
            <a key={item.label} href={item.href} className="hover:text-primary transition-colors">
              {item.label}
            </a>
          ))}
        </nav>
      </div>
    </footer>
  )
}
