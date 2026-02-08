"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/shared/lib/utils"

const buttonVariants = cva(
  "btn",
  {
    variants: {
      variant: {
        default: "btn-primary",
        secondary: "btn-secondary",
        outline: "btn-secondary",
        ghost: "hover:bg-white/5 text-text-primary",
        destructive: "bg-error text-white hover:bg-error/90",
        link: "text-accent hover:underline p-0 h-auto bg-transparent",
      },
      size: {
        default: "",
        sm: "py-2 px-4 text-xs",
        lg: "py-4 px-8 text-lg",
        icon: "w-10 h-10 p-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends ComponentProps<"button">,
    VariantProps<typeof buttonVariants> {}

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
