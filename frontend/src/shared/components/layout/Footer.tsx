export function Footer() {
  return (
    <footer className="w-full mt-20 pb-12 overflow-hidden">
      {/* Long decorative line */}
      <div className="w-[200vw] h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent -ml-[50vw] mb-12" />
      
      <div className="container flex flex-col md:flex-row justify-between items-center gap-8">
        <div className="space-y-2 text-center md:text-left">
          <span className="text-xl font-black italic tracking-tighter text-primary uppercase">M99</span>
          <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-muted-foreground/40">
            © 2026 Cinematic Intelligence
          </p>
        </div>

        <nav className="flex gap-10 text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60">
          <a href="#" className="hover:text-primary transition-colors">Privacy</a>
          <a href="#" className="hover:text-primary transition-colors">Terms</a>
          <a href="#" className="hover:text-primary transition-colors">API</a>
          <a href="#" className="hover:text-primary transition-colors">Contact</a>
        </nav>
      </div>
    </footer>
  )
}