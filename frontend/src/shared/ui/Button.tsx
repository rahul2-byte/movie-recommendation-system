"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/shared/lib/utils"

const buttonVariants = cva(
  "focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-5 text-sm font-bold transition-[color,background-color,border-color,opacity,transform] duration-200 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-45",
  {
    variants: {
      variant: {
        default: "bg-crimson text-white hover:bg-crimson-bright",
        secondary: "border border-line bg-panel text-paper hover:border-muted",
        outline:
          "border border-line bg-transparent text-paper hover:border-muted",
        ghost: "text-paper hover:bg-panel",
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
