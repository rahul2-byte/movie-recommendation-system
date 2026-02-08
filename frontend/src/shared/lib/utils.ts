import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatMovieTitle(title: string | null | undefined): string {
  if (!title) return "Untitled Movie"
  // Basic cleaning if needed, otherwise just return the title
  return title
}