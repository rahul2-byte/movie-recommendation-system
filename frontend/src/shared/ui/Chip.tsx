"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"

const chipVariants = cva(
  "flex items-center gap-2 rounded-full bg-gray-100 px-3 py-1",
  {
    variants: {},
    defaultVariants: {},
  }
)

export interface ChipProps
  extends ComponentProps<"span">,
    VariantProps<typeof chipVariants> {}

const Chip = forwardRef<HTMLSpanElement, ChipProps>(
  ({ className, ...props }, ref) => {
    return (
      <span
        className={chipVariants({ className })}
        ref={ref}
        {...props}
      />
    )
  }
)
Chip.displayName = "Chip"

const chipCloseButtonVariants = cva("text-gray-500 hover:text-black", {
  variants: {},
  defaultVariants: {},
})

export interface ChipCloseButtonProps
  extends ComponentProps<"button">,
    VariantProps<typeof chipCloseButtonVariants> {}

const ChipCloseButton = forwardRef<HTMLButtonElement, ChipCloseButtonProps>(
  ({ className, ...props }, ref) => {
    return (
      <button
        className={chipCloseButtonVariants({ className })}
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
