"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"

const cardVariants = cva("rounded-lg border bg-card text-card-foreground shadow-md", {
  variants: {},
  defaultVariants: {},
})

const Card = forwardRef<HTMLDivElement, ComponentProps<"div">>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cardVariants({ className })}
      {...props}
    />
  )
)
Card.displayName = "Card"

const cardHeaderVariants = cva("flex flex-col space-y-1.5 p-6", {
  variants: {},
  defaultVariants: {},
})

const CardHeader = forwardRef<HTMLDivElement, ComponentProps<"div">>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cardHeaderVariants({ className })}
      {...props}
    />
  )
)
CardHeader.displayName = "CardHeader"

const cardTitleVariants = cva("text-lg font-semibold leading-none tracking-tight", {
  variants: {},
  defaultVariants: {},
})

const CardTitle = forwardRef<HTMLParagraphElement, ComponentProps<"p">>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cardTitleVariants({ className })}
      {...props}
    />
  )
)
CardTitle.displayName = "CardTitle"

const cardDescriptionVariants = cva("text-sm text-muted-foreground", {
  variants: {},
  defaultVariants: {},
})

const CardDescription = forwardRef<HTMLParagraphElement, ComponentProps<"p">>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cardDescriptionVariants({ className })}
      {...props}
    />
  )
)
CardDescription.displayName = "CardDescription"

const cardContentVariants = cva("p-6 pt-0", {
  variants: {},
  defaultVariants: {},
})

const CardContent = forwardRef<HTMLDivElement, ComponentProps<"div">>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cardContentVariants({ className })}
      {...props}
    />
  )
)
CardContent.displayName = "CardContent"

const cardFooterVariants = cva("flex items-center p-6 pt-0", {
  variants: {},
  defaultVariants: {},
})

const CardFooter = forwardRef<HTMLDivElement, ComponentProps<"div">>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cardFooterVariants({ className })}
      {...props}
    />
  )
)
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
