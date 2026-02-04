"use client"

import { LazyMotion, domAnimation, m } from "framer-motion"

export function PageTransition({ children }: { children: React.ReactNode }) {
  return (
    <LazyMotion features={domAnimation} strict>
      <m.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        {children}
      </m.div>
    </LazyMotion>
  )
}
