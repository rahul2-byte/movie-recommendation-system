"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/shared/lib/utils"

const buttonVariants = cva(
  "inline-flex min-h-11 items-center justify-center gap-2 px-4 text-sm font-bold transition-colors disabled:cursor-not-allowed disabled:opacity-45",
  {
    variants: {
      variant: {
        default: "bg-crimson text-white hover:bg-crimson-bright",
        secondary:
          "border border-line bg-white/[0.03] text-paper hover:border-muted hover:bg-white/[0.06]",
        outline:
          "border border-line bg-transparent text-paper hover:border-muted",
        ghost: "text-paper hover:bg-white/[0.06]",
        destructive: "bg-danger text-white hover:bg-danger/90",
        link: "min-h-0 p-0 text-crimson hover:text-paper",
      },
      size: {
        default: "",
        sm: "min-h-9 px-3 text-xs",
        lg: "min-h-12 px-6 text-base",
        icon: "size-10 min-h-0 p-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends ComponentProps<"button">, VariantProps<typeof buttonVariants> {}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size }), className)}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
