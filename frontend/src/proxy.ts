import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Proxy function to set security headers (formerly Middleware).
 * Following best practices for production deployment.
 */
export function proxy(request: NextRequest) {
  const response = NextResponse.next();

  // 1. Content Security Policy (Basic)
  // In a real production app, you'd refine this based on your specific needs.
  // Note: Next.js has some specific requirements for 'script-src'
  const cspHeader = `
    default-src 'self';
    script-src 'self' 'unsafe-eval' 'unsafe-inline';
    style-src 'self' 'unsafe-inline';
    img-src 'self' blob: data: https://image.tmdb.org;
    font-src 'self' data:;
    object-src 'none';
    base-uri 'self';
    form-action 'self';
    frame-ancestors 'none';
    connect-src 'self' ${process.env.NEXT_PUBLIC_API_BASE || ""};
    upgrade-insecure-requests;
  `.replace(/\s{2,}/g, " ").trim();

  response.headers.set("Content-Security-Policy", cspHeader);

  // 2. Strict-Transport-Security (HSTS)
  // Forces HTTPS. Max-age is 1 year.
  response.headers.set(
    "Strict-Transport-Security",
    "max-age=31536000; includeSubDomains; preload"
  );

  // 3. X-Content-Type-Options
  // Prevents MIME type sniffing.
  response.headers.set("X-Content-Type-Options", "nosniff");

  // 4. X-Frame-Options
  // Prevents clickjacking attacks by disallowing embedding in iframes.
  response.headers.set("X-Frame-Options", "DENY");

  // 5. Referrer-Policy
  // Controls how much referrer information is included with requests.
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");

  // 6. Permissions-Policy
  // Restricts access to sensitive browser features.
  response.headers.set(
    "Permissions-Policy",
    "camera=(), microphone=(), geolocation=(), interest-cohort=()"
  );

  return response;
}

// Apply middleware to all routes except static files and API routes handled by Next.js
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (internal API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
