"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"

const modalHeaderVariants = cva(
  "mb-6 flex items-center justify-between",
  {
    variants: {},
    defaultVariants: {},
  }
)

export interface ModalHeaderProps
  extends ComponentProps<"header">,
    VariantProps<typeof modalHeaderVariants> {}

const ModalHeader = forwardRef<HTMLElement, ModalHeaderProps>(
  ({ className, ...props }, ref) => {
    return (
      <header
        className={modalHeaderVariants({ className })}
        ref={ref}
        {...props}
      />
    )
  }
)
ModalHeader.displayName = "ModalHeader"

export { ModalHeader, modalHeaderVariants }
