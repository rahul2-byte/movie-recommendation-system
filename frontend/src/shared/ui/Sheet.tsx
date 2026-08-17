"use client"

import { forwardRef } from "react"
import type { HTMLAttributes } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { X } from "lucide-react"
import * as SheetPrimitive from "@radix-ui/react-dialog"

const Sheet = SheetPrimitive.Root

const SheetTrigger = SheetPrimitive.Trigger

const SheetClose = SheetPrimitive.Close

const sheetPortalVariants = cva("fixed inset-0 z-50 flex", {
  variants: {
    position: {
      top: "items-start",
      bottom: "items-end",
      left: "justify-start",
      right: "justify-end",
    },
  },
  defaultVariants: { position: "right" },
})

interface SheetPortalProps
  extends
    SheetPrimitive.DialogPortalProps,
    VariantProps<typeof sheetPortalVariants> {}

const SheetPortal = ({ position, children, ...props }: SheetPortalProps) => (
  <SheetPrimitive.Portal {...props}>
    <div className={sheetPortalVariants({ position })}>{children}</div>
  </SheetPrimitive.Portal>
)
SheetPortal.displayName = SheetPrimitive.Portal.displayName

const SheetOverlay = forwardRef<
  React.ElementRef<typeof SheetPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof SheetPrimitive.Overlay>
>(({ ...props }, ref) => (
  <SheetPrimitive.Overlay
    className="fixed inset-0 z-50 bg-ink/75 backdrop-blur-sm transition-all duration-150 data-[state=closed]:animate-out data-[state=closed]:fade-out data-[state=open]:fade-in"
    {...props}
    ref={ref}
  />
))
SheetOverlay.displayName = SheetPrimitive.Overlay.displayName

const sheetVariants = cva(
  "fixed z-50 scale-100 gap-4 border border-line bg-panel p-5 text-paper opacity-100 shadow-xl shadow-ink/20",
  {
    variants: {
      position: {
        top: "animate-in slide-in-from-top w-full duration-300",
        bottom: "animate-in slide-in-from-bottom w-full duration-300",
        left: "animate-in slide-in-from-left h-full duration-300",
        right: "animate-in slide-in-from-right h-full duration-300",
      },
      size: {
        content: "",
        default: "",
        sm: "",
        lg: "",
        xl: "",
        full: "",
      },
    },
    compoundVariants: [
      { position: ["top", "bottom"], size: "content", class: "max-h-screen" },
      { position: ["top", "bottom"], size: "default", class: "h-1/3" },
      { position: ["top", "bottom"], size: "sm", class: "h-1/4" },
      { position: ["top", "bottom"], size: "lg", class: "h-1/2" },
      { position: ["top", "bottom"], size: "xl", class: "h-5/6" },
      { position: ["top", "bottom"], size: "full", class: "h-screen" },
      { position: ["right", "left"], size: "content", class: "max-w-screen" },
      { position: ["right", "left"], size: "default", class: "w-1/3" },
      { position: ["right", "left"], size: "sm", class: "w-1/4" },
      { position: ["right", "left"], size: "lg", class: "w-1/2" },
      { position: ["right", "left"], size: "xl", class: "w-5/6" },
      { position: ["right", "left"], size: "full", class: "w-screen" },
    ],
    defaultVariants: {
      position: "right",
      size: "default",
    },
  }
)

export interface SheetContentProps
  extends
    React.ComponentPropsWithoutRef<typeof SheetPrimitive.Content>,
    VariantProps<typeof sheetVariants> {}

const SheetContent = forwardRef<
  React.ElementRef<typeof SheetPrimitive.Content>,
  SheetContentProps
>(({ position, size, className, children, ...props }, ref) => (
  <SheetPortal position={position}>
    <SheetOverlay />
    <SheetPrimitive.Content
      ref={ref}
      className={sheetVariants({ position, size, className })}
      {...props}
    >
      {children}
      <SheetPrimitive.Close className="focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-crimson absolute right-4 top-4 grid size-9 place-items-center rounded-full text-muted transition-colors hover:bg-canvas hover:text-paper disabled:pointer-events-none">
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </SheetPrimitive.Close>
    </SheetPrimitive.Content>
  </SheetPortal>
))
SheetContent.displayName = SheetPrimitive.Content.displayName

const SheetHeader = ({ ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className="flex flex-col gap-2 text-center sm:text-left" {...props} />
)
SheetHeader.displayName = "SheetHeader"

const SheetFooter = ({ ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div
    className="flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2"
    {...props}
  />
)
SheetFooter.displayName = "SheetFooter"

const SheetTitle = forwardRef<
  React.ElementRef<typeof SheetPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof SheetPrimitive.Title>
>(({ ...props }, ref) => (
  <SheetPrimitive.Title
    ref={ref}
    className="font-display text-2xl text-paper"
    {...props}
  />
))
SheetTitle.displayName = SheetPrimitive.Title.displayName

const SheetDescription = forwardRef<
  React.ElementRef<typeof SheetPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof SheetPrimitive.Description>
>(({ ...props }, ref) => (
  <SheetPrimitive.Description
    ref={ref}
    className="text-sm leading-6 text-muted"
    {...props}
  />
))
SheetDescription.displayName = SheetPrimitive.Description.displayName

export {
  Sheet,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
}
