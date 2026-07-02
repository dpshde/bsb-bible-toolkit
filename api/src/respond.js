// HTTP response helpers shared across all Worker route handlers.
// Centralizes CORS, JSON content-type, cache headers, and the X-Origin header.

export const VERSION = "1.0.0";

// Translation identification included in all API responses so consumers can
// identify the source text without out-of-band information.
export const TRANSLATION_ID = "BSB";
export const TRANSLATION_NAME = "Berean Standard Bible";

// Immutable one-year cache directive for verse/chapter/book/passage content.
// (VAL-API-030, VAL-API-031, VAL-API-032)
export const IMMUTABLE_CACHE = "public, max-age=31536000, immutable";

// Valid cross-reference source identifiers. Used for `?source=` filter
// validation. Unknown sources silently filter to empty (VAL-API-022, VAL-API-045).
export const VALID_SOURCES = ["bsb-footnote", "tsk", "acai", "theographic"];

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "86400",
};

// Build response headers. `origin` is the cache tier that served the request
// ("edge" | "r2" | "arweave"). `cacheControl` is omitted for non-cacheable
// responses (errors, health).
function buildHeaders({ origin, cacheControl, extra = {} }) {
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    "X-Origin": origin,
    ...CORS_HEADERS,
  };
  if (cacheControl) headers["Cache-Control"] = cacheControl;
  for (const [k, v] of Object.entries(extra)) headers[k] = v;
  return headers;
}

// JSON success response (200 by default).
export function jsonResponse(body, { status = 200, origin = "r2", cacheControl = null, extra = {} } = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: buildHeaders({ origin, cacheControl, extra }),
  });
}

// JSON error response. CORS headers are always present, even on errors
// (VAL-API-028, VAL-API-034). Errors never get immutable cache headers.
export function errorResponse(status, message, { origin = "r2", extra = {} } = {}) {
  return new Response(JSON.stringify({ error: message, status }), {
    status,
    headers: buildHeaders({ origin, cacheControl: null, extra }),
  });
}

// CORS preflight (OPTIONS) handler. Always returns 204 with CORS headers
// (VAL-API-029).
export function optionsResponse() {
  return new Response(null, {
    status: 204,
    headers: buildHeaders({ origin: "edge", cacheControl: null }),
  });
}

export { buildHeaders, CORS_HEADERS };
