import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Proxy function to set security headers.
 * Following best practices for Next.js 16 conventions.
 */
export default function proxy(request: NextRequest) {
  const response = NextResponse.next();

  // 1. Content Security Policy (Basic)
  const cspHeader = `
    default-src 'self';
    script-src 'self' 'unsafe-eval' 'unsafe-inline';
    style-src 'self' 'unsafe-inline';
    img-src 'self' blob: data: https://image.tmdb.org https://m.media-amazon.com https://ia.media-imdb.com;
    font-src 'self' data:;
    object-src 'none';
    base-uri 'self';
    form-action 'self';
    frame-ancestors 'none';
    connect-src 'self' ${process.env.NEXT_PUBLIC_API_BASE ? new URL(process.env.NEXT_PUBLIC_API_BASE).origin : ""};
    upgrade-insecure-requests;
  `.replace(/\s{2,}/g, " ").trim();

  response.headers.set("Content-Security-Policy", cspHeader);

  // 2. Strict-Transport-Security (HSTS)
  response.headers.set(
    "Strict-Transport-Security",
    "max-age=31536000; includeSubDomains; preload"
  );

  // 3. X-Content-Type-Options
  response.headers.set("X-Content-Type-Options", "nosniff");

  // 4. X-Frame-Options
  response.headers.set("X-Frame-Options", "DENY");

  // 5. Referrer-Policy
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");

  // 6. Permissions-Policy
  response.headers.set(
    "Permissions-Policy",
    "camera=(), microphone=(), geolocation=(), interest-cohort=()"
  );

  return response;
}

// Apply proxy to all routes except static files
export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};