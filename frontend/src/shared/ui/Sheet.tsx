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
    className="fixed inset-0 z-50 bg-background/70 backdrop-blur-sm transition-all duration-150 data-[state=closed]:animate-out data-[state=closed]:fade-out data-[state=open]:fade-in"
    {...props}
    ref={ref}
  />
))
SheetOverlay.displayName = SheetPrimitive.Overlay.displayName

const sheetVariants = cva(
  "fixed z-50 scale-100 gap-4 bg-surface p-card opacity-100 shadow-card border border-border",
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
      <SheetPrimitive.Close className="absolute top-4 right-4 rounded-pill p-tight text-muted-foreground transition-colors hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-surface-strong">
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </SheetPrimitive.Close>
    </SheetPrimitive.Content>
  </SheetPortal>
))
SheetContent.displayName = SheetPrimitive.Content.displayName

const SheetHeader = ({ ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div
    className="flex flex-col space-y-tight text-center sm:text-left"
    {...props}
  />
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
    className="text-h3 font-semibold text-foreground"
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
    className="text-body text-muted-foreground"
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
