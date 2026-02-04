"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/shared/lib/utils"

const chipVariants = cva(
  "flex items-center gap-2 rounded-pill bg-surface-strong px-chip py-tight text-caption text-muted-foreground border border-border"
)

export interface ChipProps
  extends ComponentProps<"span">,
    VariantProps<typeof chipVariants> {}

const Chip = forwardRef<HTMLSpanElement, ChipProps>(
  ({ className, ...props }, ref) => {
    return (
      <span className={cn(chipVariants(), className)} ref={ref} {...props} />
    )
  }
)
Chip.displayName = "Chip"

const chipCloseButtonVariants = cva(
  "text-muted-foreground hover:text-foreground transition-colors"
)

export interface ChipCloseButtonProps
  extends ComponentProps<"button">,
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
