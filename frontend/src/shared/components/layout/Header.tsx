"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Sheet, SheetContent, SheetTrigger } from "@/shared/ui/Sheet"
import { Button } from "@/shared/ui/Button"
import { Menu } from "lucide-react"

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/my-list", label: "My List" },
  { href: "/project", label: "Project" },
  { href: "/about", label: "About" },
] as const

export function Header() {
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/5 bg-background/40 backdrop-blur-xl transition-all">
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-12">
          <Link href="/" className="flex items-center space-x-2 group">
            <span className="text-xl font-black tracking-tighter text-primary uppercase italic transition-transform group-hover:skew-x-[-10deg]">
              M99
            </span>
          </Link>
          <nav className="hidden md:flex items-center space-x-8 nav-text text-muted-foreground/70">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`transition-colors hover:text-primary ${
                    isActive ? "text-primary font-bold" : ""
                  }`}
                >
                  {item.label}
                </Link>
              )
            })}
          </nav>
        </div>
        
        <div className="flex items-center gap-4">
           {/* Mobile Menu */}
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="sm" className="md:hidden">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="bg-background border-r-white/5">
              <div className="flex flex-col gap-8 mt-12">
                {NAV_ITEMS.map((item) => (
                  <Link key={item.href} href={item.href} className="text-2xl font-bold uppercase tracking-widest">
                    {item.label}
                  </Link>
                ))}
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  )
}