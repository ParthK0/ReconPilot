/**
 * frontend/lib/api.ts
 * ===================
 * Configurable API client base URL resolver.
 * Defaults to http://localhost:8000 for local development,
 * and reads NEXT_PUBLIC_API_URL in production / cloud environments.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
