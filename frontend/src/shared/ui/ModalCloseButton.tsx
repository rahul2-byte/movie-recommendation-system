"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Button } from "./Button"
import { cn } from "@/shared/lib/utils"

const modalCloseButtonVariants = cva("text-muted-foreground")

export interface ModalCloseButtonProps
  extends ComponentProps<"button">,
    VariantProps<typeof modalCloseButtonVariants> {}

const ModalCloseButton = forwardRef<HTMLButtonElement, ModalCloseButtonProps>(
  ({ className, ...props }, ref) => {
    return (
      <Button
        variant="ghost"
        size="icon"
        className={cn(modalCloseButtonVariants(), className)}
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
