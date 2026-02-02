"use client"

import { useState, Suspense, lazy } from "react"
import { Button } from "@/shared/ui/Button"
import { Sparkles } from "lucide-react"

const RecommendationModal = lazy(() =>
  import("./RecommendationModal").then((module) => ({
    default: module.RecommendationModal,
  }))
)

export function RecommendationTrigger() {
    const [open, setOpen] = useState(false)

    return (
        <>
            <Button 
                onClick={() => setOpen(true)} 
                size="lg" 
                className="rounded-full px-10 py-8 text-2xl font-black transition-all hover:scale-105 active:scale-95 bg-primary text-primary-foreground retro-shadow italic uppercase tracking-tighter"
            >
                <Sparkles className="mr-3 h-6 w-6 fill-current" />
                Start My Reel
            </Button>

            {open && (
                <Suspense fallback={null}>
                    <RecommendationModal onClose={() => setOpen(false)} />
                </Suspense>
            )}
        </>
    )
}
