import "./globals.css"
import type { Metadata } from "next"
import { Header } from "@/components/layout/Header"
import { Footer } from "@/components/layout/Footer"
import { RecommendationProvider } from "@/lib/context/RecommendationContext"

export const metadata: Metadata = {
  title: "Movies99",
  description: "ML-powered movie recommendation system",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased" suppressHydrationWarning>
        <Header />
        <RecommendationProvider>
          {children}
        </RecommendationProvider>
        <Footer />
      </body>
    </html>
  )
}
