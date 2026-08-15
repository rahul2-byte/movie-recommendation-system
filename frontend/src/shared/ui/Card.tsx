"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva } from "class-variance-authority"
import { cn } from "@/shared/lib/utils"

const cardVariants = cva(
  "rounded-card border border-border bg-surface text-foreground shadow-card"
)

const Card = forwardRef<HTMLDivElement, ComponentProps<"div">>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn(cardVariants(), className)} {...props} />
  )
)
Card.displayName = "Card"

const cardHeaderVariants = cva("flex flex-col space-y-tight p-card")

const CardHeader = forwardRef<HTMLDivElement, ComponentProps<"div">>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn(cardHeaderVariants(), className)} {...props} />
  )
)
CardHeader.displayName = "CardHeader"

const cardTitleVariants = cva("text-h3 font-semibold leading-h3")

const CardTitle = forwardRef<HTMLParagraphElement, ComponentProps<"p">>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn(cardTitleVariants(), className)} {...props} />
  )
)
CardTitle.displayName = "CardTitle"

const cardDescriptionVariants = cva("text-body text-muted-foreground")

const CardDescription = forwardRef<HTMLParagraphElement, ComponentProps<"p">>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cn(cardDescriptionVariants(), className)}
      {...props}
    />
  )
)
CardDescription.displayName = "CardDescription"

const cardContentVariants = cva("p-card pt-0")

const CardContent = forwardRef<HTMLDivElement, ComponentProps<"div">>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardContentVariants(), className)}
      {...props}
    />
  )
)
CardContent.displayName = "CardContent"

const cardFooterVariants = cva("flex items-center p-card pt-0")

const CardFooter = forwardRef<HTMLDivElement, ComponentProps<"div">>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn(cardFooterVariants(), className)} {...props} />
  )
)
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
