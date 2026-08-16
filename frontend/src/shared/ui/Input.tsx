"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/shared/lib/utils"

const inputVariants = cva(
  "flex h-12 w-full border border-line bg-ink px-4 text-base text-paper placeholder:text-dim focus-visible:border-crimson focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {},
    defaultVariants: {},
  }
)

export interface InputProps
  extends ComponentProps<"input">, VariantProps<typeof inputVariants> {}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => {
    return (
      <input className={cn(inputVariants(), className)} ref={ref} {...props} />
    )
  }
)
Input.displayName = "Input"

export { Input, inputVariants }
