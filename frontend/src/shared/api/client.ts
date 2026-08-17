import { env } from "@/shared/config/env"

export async function apiClient<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const cleanBase = env.NEXT_PUBLIC_API_BASE.replace(/\/$/, "")
  const url = `${cleanBase}/api/v1${path}`

  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `API Failure: ${response.status}`)
  }

  return (await response.json()) as T
}
