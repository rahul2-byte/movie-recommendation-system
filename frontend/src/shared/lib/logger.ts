import { env } from "@/shared/config/env";

/**
 * Lightweight logger for production and development.
 * In production, it can be extended to send logs to external services like Sentry or Axiom.
 */
const isProd = env.NODE_ENV === "production";

export const logger = {
  debug: (...args: any[]) => {
    if (!isProd) {
      console.debug("DEBUG:", ...args);
    }
  },
  
  info: (...args: any[]) => {
    if (!isProd) {
      console.info("INFO:", ...args);
    }
  },
  
  warn: (...args: any[]) => {
    // We might want to see warnings even in prod, but with caution
    console.warn("WARN:", ...args);
  },
  
  error: (...args: any[]) => {
    // Errors should always be logged
    console.error("ERROR:", ...args);
    
    // In production, this is where you'd call Sentry.captureException(args[0])
  },
};
