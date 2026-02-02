import "./globals.css"
import type { Metadata } from "next"
import { Inter, Playfair_Display, Rubik } from "next/font/google"
import { Header } from "@/shared/components/layout/Header"
import { Footer } from "@/shared/components/layout/Footer"
import { RecommendationProvider } from "@/features/recommendations/context/RecommendationContext"
import { Providers } from "@/shared/components/Providers"
import { PageTransition } from "@/shared/components/layout/PageTransition"

const inter = Inter({ 
  subsets: ["latin"], 
  variable: "--font-inter",
  display: "swap"
})

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-playfair",
  display: "swap"
})

const rubik = Rubik({
  subsets: ["latin"],
  variable: "--font-rubik",
  display: "swap"
})

export const metadata: Metadata = {
  title: "Movies99 | Cinematic Intelligence",
  description: "Find your next cinematic obsession with AI.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${playfair.variable} ${rubik.variable} font-sans selection:bg-primary selection:text-primary-foreground`}>
        <Providers>
          <RecommendationProvider>
            <div className="flex min-h-screen flex-col items-center">
              <Header />
              <main className="w-full flex-grow flex flex-col items-center">
                <PageTransition>
                  {children}
                </PageTransition>
              </main>
              <Footer />
            </div>
          </RecommendationProvider>
        </Providers>
      </body>
    </html>
  )
}