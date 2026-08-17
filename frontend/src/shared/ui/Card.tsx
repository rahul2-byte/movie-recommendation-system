"use client"

import { forwardRef } from "react"
import type { ComponentProps } from "react"
import { cva } from "class-variance-authority"
import { cn } from "@/shared/lib/utils"

const cardVariants = cva(
  "rounded-2xl border border-line bg-panel text-paper shadow-[0_18px_50px_rgba(25,25,28,0.06)]"
)

const Card = forwardRef<HTMLDivElement, ComponentProps<"div">>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn(cardVariants(), className)} {...props} />
  )
)
Card.displayName = "Card"

const cardHeaderVariants = cva("flex flex-col gap-2 p-5")

const CardHeader = forwardRef<HTMLDivElement, ComponentProps<"div">>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn(cardHeaderVariants(), className)} {...props} />
  )
)
CardHeader.displayName = "CardHeader"

const cardTitleVariants = cva("font-display text-2xl leading-tight text-paper")

const CardTitle = forwardRef<HTMLParagraphElement, ComponentProps<"p">>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn(cardTitleVariants(), className)} {...props} />
  )
)
CardTitle.displayName = "CardTitle"

const cardDescriptionVariants = cva("text-sm leading-6 text-muted")

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

const cardContentVariants = cva("p-5 pt-0")

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

const cardFooterVariants = cva("flex items-center p-5 pt-0")

const CardFooter = forwardRef<HTMLDivElement, ComponentProps<"div">>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn(cardFooterVariants(), className)} {...props} />
  )
)
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
