"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Button } from "./Button"

const modalCloseButtonVariants = cva(
  "text-gray-500",
  {
    variants: {},
    defaultVariants: {},
  }
)

export interface ModalCloseButtonProps
  extends ComponentProps<"button">,
    VariantProps<typeof modalCloseButtonVariants> {}

const ModalCloseButton = forwardRef<HTMLButtonElement, ModalCloseButtonProps>(
  ({ className, ...props }, ref) => {
    return (
      <Button
        variant="ghost"
        className={modalCloseButtonVariants({ className })}
        ref={ref}
        {...props}
      >
        ✕
      </Button>
    )
  }
)
ModalCloseButton.displayName = "ModalCloseButton"

export { ModalCloseButton, modalCloseButtonVariants }
