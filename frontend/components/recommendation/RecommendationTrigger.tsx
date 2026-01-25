"use client"

import { useState } from "react"
import { RecommendationModal } from "./RecommendationModal"

export function RecommendationTrigger() {
    const [open, setOpen] = useState(false)

    return (
        <>
            <button
                onClick={() => setOpen(true)}
                className="rounded-xl bg-gradient-to-r from-amber-400 to-rose-400 px-8 py-4 text-lg font-semibold text-black shadow-lg hover:scale-[1.02] transition"
            >
                Get Movie Recommendations
            </button>

            {open && <RecommendationModal onClose={() => setOpen(false)} />}
        </>
    )
}
