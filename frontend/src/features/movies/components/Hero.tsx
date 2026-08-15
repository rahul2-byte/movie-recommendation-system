"use client"

import Link from "next/link"
import { LazyMotion, domAnimation, m } from "framer-motion"
import { ArrowRight } from "lucide-react"

export function Hero() {
  return (
    <section className="section-hero relative">
      <div className="container">
        <LazyMotion features={domAnimation} strict>
          <div className="hero-content mx-auto text-center max-w-[900px]">
            <m.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="label-accent mb-6 block"
            >
              AI-POWERED CURATION
            </m.p>

            <m.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="heading-hero mb-8"
            >
              Cinema,
              <br />
              <em className="italic font-serif">Understood.</em>
            </m.h1>

            <m.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-body mb-12 max-w-[600px] mx-auto"
            >
              Discover films based on mood, tone, and cinematic DNA. Not just
              genres.
            </m.p>

            <m.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Link href="/setup" className="btn btn-primary">
                Curate Your Night
                <ArrowRight className="btn-icon" />
              </Link>
            </m.div>
          </div>
        </LazyMotion>
      </div>
    </section>
  )
}
