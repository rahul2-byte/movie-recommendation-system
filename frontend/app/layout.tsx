import "./globals.css"
import type { Metadata } from "next"
import { Header } from "@/components/layout/Header"
import { Footer } from "@/components/layout/Footer"

export const metadata: Metadata = {
  title: "CineSeek",
  description: "ML-powered movie recommendation system",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-black text-white antialiased">
      <Header />
        <main className="pt-16">{children}</main>
        <Footer />
      </body>
    </html>
  )
}
