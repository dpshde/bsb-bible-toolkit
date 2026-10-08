// Workers Rate Limiting for the public bsb-api Worker.
//
// Binding: RATE_LIMITER in wrangler.toml ([[ratelimits]], namespace_id 847220).
// 100 requests per 60 seconds per client IP. The platform window is per
// Cloudflare location, not global. There is no API key on this service, so
// CF-Connecting-IP is the client key (Cloudflare overwrites it at the edge).
//
// CORS preflight (OPTIONS) is not counted; worker.js returns that before
// calling enforceRateLimit. When the binding is absent (a local experiment
// that removed it), requests are allowed. Production wrangler.toml always
// declares the binding.

import { errorResponse } from "./respond.js";

// Keep these in sync with [ratelimits.simple] in wrangler.toml.
export const RATE_LIMIT_REQUESTS = 100;
export const RATE_LIMIT_PERIOD_SECONDS = 60;

const MAX_KEY_LENGTH = 128;

// Stable per-client key. Empty or missing addresses share one bucket so a
// request cannot dodge the limiter by omitting the header.
export function clientRateLimitKey(request) {
  const raw = request && request.headers ? request.headers.get("CF-Connecting-IP") : "";
  const ip = typeof raw === "string" ? raw.trim() : "";
  if (!ip) return "unknown";
  return ip.slice(0, MAX_KEY_LENGTH);
}

// Returns a 429 Response when the caller is over the limit, or null when the
// request may proceed.
export async function enforceRateLimit(request, env) {
  const limiter = env && env.RATE_LIMITER;
  if (!limiter || typeof limiter.limit !== "function") return null;

  const key = clientRateLimitKey(request);
  const { success } = await limiter.limit({ key });
  if (success) return null;

  return errorResponse(429, "Too many requests. Try again later.", {
    origin: "edge",
    cacheControl: "no-store",
    extra: {
      "Retry-After": String(RATE_LIMIT_PERIOD_SECONDS),
      "Access-Control-Expose-Headers": "Retry-After",
    },
  });
}
