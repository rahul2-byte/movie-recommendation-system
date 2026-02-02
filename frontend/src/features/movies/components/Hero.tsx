"use client"

import { RecommendationTrigger } from "@/features/recommendations/components/RecommendationTrigger"
import { motion } from "framer-motion"

export function Hero() {
  return (
    <section className="relative w-full h-[calc(100vh-64px)] flex items-center justify-center overflow-hidden bg-background px-6 mb-20">
      {/* Soft color bleed background */}
      <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_50%_50%,_var(--tw-gradient-stops))] from-primary/20 via-transparent to-transparent" />
      
      <div className="relative z-10 w-full max-w-7xl mx-auto text-center">
        <motion.span 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 inline-block text-[10px] font-bold uppercase tracking-[0.5em] text-primary/80"
        >
          Curating the Extraordinary
        </motion.span>
        
        <motion.h1 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-7xl md:text-[10rem] font-bold leading-[0.8] mb-12 text-white text-balance"
        >
          Cinematic <br /> 
          <span className="text-primary italic font-light drop-shadow-[0_0_30px_rgba(249,177,122,0.3)]">
            Intelligence
          </span>
        </motion.h1>

        <motion.p 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="mt-8 text-lg md:text-xl text-muted-foreground/60 font-medium max-w-xl mx-auto leading-relaxed tracking-wide"
        >
          Move beyond the algorithm. Discover films that resonate with your soul through advanced neural discovery.
        </motion.p>

        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
          className="mt-16"
        >
          <RecommendationTrigger />
        </motion.div>
      </div>
    </section>
  )
}
