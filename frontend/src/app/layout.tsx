import "./globals.css"
import type { Metadata } from "next"
import { Space_Grotesk, Fraunces } from "next/font/google"
import { Header } from "@/shared/ui/layout/Header"
import { Footer } from "@/shared/ui/layout/Footer"
import { RecommendationProvider } from "@/features/recommendations/context/RecommendationContext"
import { Providers } from "@/shared/ui/Providers"

const space = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space",
  display: "swap",
})

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  display: "swap",
})

export const metadata: Metadata = {
  title: "Movies99 | Premium Film Discovery",
  description: "Curated recommendations with a premium cinematic feel.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body
        className={`${space.variable} ${fraunces.variable} font-sans selection:bg-primary selection:text-primary-foreground`}
      >
        <Providers>
          <RecommendationProvider>
            <div className="flex min-h-screen flex-col">
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
