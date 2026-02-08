import { env } from "@/shared/config/env";
import { z } from "zod";

/**
 * Production-grade API Client with Zod validation.
 */
export async function apiClient<T>(
  path: string,
  options?: RequestInit & { schema?: z.ZodSchema<T> }
): Promise<T> {
  const cleanBase = env.NEXT_PUBLIC_API_BASE.replace(/\/$/, "");
  const url = `${cleanBase}/api/v1${path}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API Failure: ${response.status}`);
  }

  const data = await response.json();

  // If a schema is provided, validate the data at the runtime boundary
  if (options?.schema) {
    const result = options.schema.safeParse(data);
    if (!result.success) {
      console.error(`[VALIDATION ERROR] ${path}:`, result.error.format());
      // In production, you'd send this to Sentry
      throw new Error("Received malformed data from the server.");
    }
    return result.data;
  }

  return data as T;
}