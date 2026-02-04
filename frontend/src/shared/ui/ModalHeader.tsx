"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/shared/lib/utils"

const modalHeaderVariants = cva("mb-stack flex items-center justify-between")

export interface ModalHeaderProps
  extends ComponentProps<"header">,
    VariantProps<typeof modalHeaderVariants> {}

const ModalHeader = forwardRef<HTMLElement, ModalHeaderProps>(
  ({ className, ...props }, ref) => {
    return (
      <header
        className={cn(modalHeaderVariants(), className)}
        ref={ref}
        {...props}
      />
    )
  }
)
ModalHeader.displayName = "ModalHeader"

export { ModalHeader, modalHeaderVariants }
