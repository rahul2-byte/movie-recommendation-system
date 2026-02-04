"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/shared/lib/utils"

const modalVariants = cva(
  "fixed inset-0 z-50 flex items-center justify-center bg-background/70 backdrop-blur-md p-gutter animate-in fade-in duration-300"
)

const modalContentVariants = cva(
  "relative w-full max-w-modal max-h-modal overflow-y-auto rounded-xl bg-surface-strong border border-border p-card shadow-hero animate-in zoom-in-95 duration-300 no-scrollbar"
)

export interface ModalProps
  extends ComponentProps<"div">,
    VariantProps<typeof modalVariants> {
  contentClassName?: string
}

const Modal = forwardRef<HTMLDivElement, ModalProps>(
  ({ className, contentClassName, children, ...props }, ref) => {
    return (
      <div className={cn(modalVariants(), className)} ref={ref} {...props}>
        <div className={cn(modalContentVariants(), contentClassName)}>
          {children}
        </div>
      </div>
    )
  }
)
Modal.displayName = "Modal"

export { Modal, modalVariants, modalContentVariants }
