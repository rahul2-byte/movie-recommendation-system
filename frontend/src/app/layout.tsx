import "./globals.css"
import type { Metadata, Viewport } from "next"
import { Manrope, Newsreader } from "next/font/google"
import { Header } from "@/shared/ui/layout/Header"
import { Footer } from "@/shared/ui/layout/Footer"
import { Providers } from "@/shared/ui/Providers"
import { PageTransition } from "@/shared/ui/motion/PageTransition"

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  display: "swap",
})

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-newsreader",
  display: "swap",
})

export const metadata: Metadata = {
  title: "M99 | Movie Recommendation System",
  description:
    "Choose movies you love and discover a ranked lineup for your next watch.",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000"
  ),
  openGraph: {
    title: "M99 Cinema",
    description: "An end-to-end movie recommendation and discovery project.",
    type: "website",
    locale: "en_US",
  },
  robots: {
    index: true,
    follow: true,
  },
}

export const viewport: Viewport = {
  themeColor: "#f4f4ef",
  width: "device-width",
  initialScale: 1,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="scroll-smooth scheme-light bg-canvas">
      <body
        className={`${manrope.variable} ${newsreader.variable} min-w-[320px] bg-canvas font-sans text-paper antialiased selection:bg-crimson selection:text-white`}
      >
        <Providers>
          <div className="flex min-h-screen flex-col overflow-x-clip">
            <Header />
            <main id="main-content" className="w-full flex-1">
              <PageTransition>{children}</PageTransition>
            </main>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  )
}
