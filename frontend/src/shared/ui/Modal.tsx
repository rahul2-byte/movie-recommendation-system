"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"

const modalVariants = cva(
  "fixed inset-0 z-[100] flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300",
  {
    variants: {},
    defaultVariants: {},
  }
)

const modalContentVariants = cva(
  "relative w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-[2.5rem] bg-card border border-white/5 p-8 shadow-2xl animate-in zoom-in-95 duration-300 no-scrollbar",
  {
    variants: {},
    defaultVariants: {},
  }
)

export interface ModalProps
  extends ComponentProps<"div">,
    VariantProps<typeof modalVariants> {
  contentClassName?: string
}

const Modal = forwardRef<HTMLDivElement, ModalProps>(
  ({ className, contentClassName, children, ...props }, ref) => {
    return (
      <div className={modalVariants({ className })} ref={ref} {...props}>
        <div className={modalContentVariants({ className: contentClassName })}>
          {children}
        </div>
      </div>
    )
  }
)
Modal.displayName = "Modal"

export { Modal, modalVariants, modalContentVariants }