import "./globals.css"
import type { Metadata, Viewport } from "next"
import { Inter } from "next/font/google"
import { Header } from "@/shared/ui/layout/Header"
import { Footer } from "@/shared/ui/layout/Footer"
import { Providers } from "@/shared/ui/Providers"
import { PageTransition } from "@/shared/ui/motion/PageTransition"

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
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
  themeColor: "#080808",
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
        className={`${inter.variable} font-sans selection:bg-accent selection:text-white`}
      >
        <Providers>
          <div className="flex min-h-screen flex-col overflow-x-clip">
            <Header />
            <main className="w-full flex-1">
              <PageTransition>{children}</PageTransition>
            </main>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  )
}
