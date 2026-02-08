import "./globals.css"
import type { Metadata } from "next"
import { Inter, Playfair_Display } from "next/font/google"
import { Header } from "@/shared/ui/layout/Header"
import { Footer } from "@/shared/ui/layout/Footer"
import { RecommendationProvider } from "@/features/recommendations/context/RecommendationContext"
import { Providers } from "@/shared/ui/Providers"

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
})

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
})

export const metadata: Metadata = {
  title: "M99 - Cinema, Understood.",
  description: "Discover films based on mood, tone, and cinematic DNA.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${playfair.variable} font-sans selection:bg-accent selection:text-black`}
      >
        <div className="grain-overlay" />
        <Providers>
          <RecommendationProvider>
            <div className="flex min-h-screen flex-col bg-black text-white">
              <Header />
              <main className="w-full flex-1">{children}</main>
              <Footer />
            </div>
          </RecommendationProvider>
        </Providers>
      </body>
    </html>
  )
}
