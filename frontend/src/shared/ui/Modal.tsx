"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/shared/lib/utils"

const modalVariants = cva("modal-overlay")

const modalContentVariants = cva("modal no-scrollbar")

export interface ModalProps
  extends ComponentProps<"div">, VariantProps<typeof modalVariants> {
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
