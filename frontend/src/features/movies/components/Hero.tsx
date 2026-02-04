"use client"

import { RecommendationTrigger } from "@/features/recommendations/components/RecommendationTrigger"
import { LazyMotion, domAnimation, m } from "framer-motion"

export function Hero() {
  return (
    <section className="relative w-full min-h-screen flex items-center overflow-hidden bg-background">
      <div className="absolute inset-0 hero-ambient opacity-70" />
      <div className="absolute -top-24 right-0 h-96 w-96 rounded-pill bg-primary/15 blur-3xl" />
      <div className="absolute bottom-0 left-0 h-80 w-80 rounded-pill bg-surface-strong/60 blur-3xl" />

      <div className="relative z-10 w-full px-gutter py-hero">
        <div className="mx-auto max-w-page grid gap-section lg:grid-cols-[1.15fr_0.85fr] items-center">
          <LazyMotion features={domAnimation} strict>
            <div className="space-y-stack">
              <m.span
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="inline-flex items-center gap-2 rounded-pill border border-primary/30 bg-primary/10 px-control-sm-x h-control-sm text-overline text-primary"
              >
                Portfolio Project · 2026 Edition
              </m.span>

              <m.h1
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.08 }}
                className="text-hero display-font text-balance"
              >
                Movies99
                <span className="text-primary"> curates</span> the perfect film
                night.
              </m.h1>

              <m.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.16 }}
                className="text-body-lg text-muted-foreground max-w-narrow leading-body"
              >
                A cinematic recommendation experience built to showcase
                full-stack product thinking: clean UX, expressive typography,
                and a machine-learning engine that does the heavy lifting.
              </m.p>

              <m.div
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.24 }}
                className="flex flex-wrap gap-4"
              >
                <RecommendationTrigger />
                <div className="flex items-center gap-3 text-caption text-muted-foreground">
                  <span className="h-2 w-2 rounded-pill bg-primary" />
                  Crafted for portfolio depth
                </div>
              </m.div>
            </div>
          </LazyMotion>

          <div className="space-y-stack">
            <div className="glass rounded-xl p-card shadow-hero">
              <div className="space-y-tight">
                <p className="text-overline text-muted-foreground/70">
                  Live signal
                </p>
                <p className="text-h2 font-semibold">
                  20 curated picks in under 300ms
                </p>
                <p className="text-body text-muted-foreground">
                  Powered by ALS recall, vector retrieval, and lightweight
                  ranking tuned for personalization.
                </p>
              </div>
            </div>

            <div className="grid gap-grid sm:grid-cols-2">
              <div className="surface rounded-lg p-card">
                <p className="text-overline text-muted-foreground/70">Stack</p>
                <p className="text-body font-semibold">Next.js · FastAPI · ML</p>
              </div>
              <div className="surface rounded-lg p-card">
                <p className="text-overline text-muted-foreground/70">Focus</p>
                <p className="text-body font-semibold">UX + model craft</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
