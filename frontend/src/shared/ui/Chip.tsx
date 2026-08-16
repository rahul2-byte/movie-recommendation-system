"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/shared/lib/utils"

const chipVariants = cva(
  "inline-flex items-center gap-2 border border-line bg-panel px-3 py-1.5 text-xs font-semibold text-muted"
)

export interface ChipProps
  extends ComponentProps<"span">, VariantProps<typeof chipVariants> {}

const Chip = forwardRef<HTMLSpanElement, ChipProps>(
  ({ className, ...props }, ref) => {
    return (
      <span className={cn(chipVariants(), className)} ref={ref} {...props} />
    )
  }
)
Chip.displayName = "Chip"

const chipCloseButtonVariants = cva(
  "text-muted transition-colors hover:text-paper"
)

export interface ChipCloseButtonProps
  extends
    ComponentProps<"button">,
    VariantProps<typeof chipCloseButtonVariants> {}

const ChipCloseButton = forwardRef<HTMLButtonElement, ChipCloseButtonProps>(
  ({ className, ...props }, ref) => {
    return (
      <button
        className={cn(chipCloseButtonVariants(), className)}
        ref={ref}
        {...props}
      >
        ✕
      </button>
    )
  }
)
ChipCloseButton.displayName = "ChipCloseButton"

export { Chip, ChipCloseButton }
