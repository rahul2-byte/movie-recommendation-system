import "./globals.css"
import type { Metadata, Viewport } from "next"
import { Inter, Playfair_Display } from "next/font/google"
import { Header } from "@/shared/ui/layout/Header"
import { Footer } from "@/shared/ui/layout/Footer"
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
  title: "M99 | Premium Cinema Curation",
  description:
    "Discover films based on mood, tone, and cinematic DNA. Your personal digital film archive.",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000"
  ),
  openGraph: {
    title: "M99 Cinema",
    description: "AI-Powered Movie Recommendations",
    type: "website",
    locale: "en_US",
  },
  robots: {
    index: true,
    follow: true,
  },
}

export const viewport: Viewport = {
  themeColor: "#121212",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
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
          <div className="flex min-h-screen flex-col bg-black text-white">
            <Header />
            <main className="w-full flex-1">{children}</main>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  )
}
