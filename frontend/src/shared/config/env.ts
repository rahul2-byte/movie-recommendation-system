import { z } from "zod"

/**
 * Schema for environment variables.
 * NEXT_PUBLIC_ variables are exposed to the browser.
 */
const envSchema = z.object({
  NEXT_PUBLIC_API_BASE: z.string().url().default("http://localhost:8080"),
  NODE_ENV: z
    .enum(["development", "production", "test"])
    .default("development"),
})

// Validate process.env against the schema
const parsed = envSchema.safeParse({
  NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE,
  NODE_ENV: process.env.NODE_ENV,
})

if (!parsed.success) {
  console.error(
    "❌ Invalid environment variables:",
    JSON.stringify(parsed.error.format(), null, 2)
  )
  throw new Error("Invalid environment variables")
}

export const env = parsed.data
