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
        className="rounded-pill px-control-lg-x text-body-lg font-semibold tracking-wide"
      >
        <Sparkles className="h-5 w-5" />
        Start my reel
      </Button>

      {open && (
        <Suspense fallback={null}>
          <RecommendationModal onClose={() => setOpen(false)} />
        </Suspense>
      )}
    </>
  )
}
