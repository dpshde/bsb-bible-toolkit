// BSB JSON API - Cloudflare Worker entry point.
//
// 4-tier cache-aside (edge cache -> R2 -> Arweave -> 503) serves the
// public-domain Berean Standard Bible as structured JSON. All Bible
// reference parsing is delegated to `grab-bcv`.
//
// R2 binding: the `BSB_DATASET` binding (declared in wrangler.toml) is
// accessed inside api/src/cache.js for the persistent cache tier.
//
// Endpoints:
//   GET  /v1/books                 - book catalog (66 books)
//   GET  /v1/book/:osis            - full book JSON
//   GET  /v1/chapter/:osis/:ch     - full chapter JSON
//   GET  /v1/verse/:osisRef        - single verse with footnotes/cross-refs/events
//   GET  /v1/passage/:ref          - grab-bcv parsed passage with range expansion
//   GET  /v1/resolve/:input        - any input format (human/OSIS/URI/URL) to canonical passage
//   GET  /v1/search?q=...          - substring search across all verses
//   GET  /v1/crossrefs/:osisRef    - cross-references (?source= filter supported)
//   GET  /v1/health                - service health, version, cache tier status
//   OPTIONS *                      - CORS preflight (204)

import {
  handleBooks,
  handleBook,
  handleChapter,
  handleVerse,
  handlePassage,
  handleResolve,
  handleSearch,
  handleCrossrefs,
  handleHealth,
} from "./src/routes.js";
import { optionsResponse, errorResponse } from "./src/respond.js";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const method = request.method.toUpperCase();

    // CORS preflight: every path answers OPTIONS with 204 + CORS headers.
    if (method === "OPTIONS") return optionsResponse();

    if (method !== "GET" && method !== "HEAD") {
      return errorResponse(405, `Method not allowed: ${method}. Use GET.`, { origin: "edge" });
    }

    const path = url.pathname;
    const params = { url, env, ctx };

    try {
      // Static route: /v1/health
      if (path === "/v1/health") return await handleHealth(params);

      // Static route: /v1/books
      if (path === "/v1/books") return await handleBooks(params);

      // Static route: /v1/search (uses query string)
      if (path === "/v1/search") return await handleSearch(params);

      // Parameterized routes.
      const verseMatch = matchRoute("/v1/verse/:osisRef", path);
      if (verseMatch) return await handleVerse({ ...params, params: verseMatch });

      const chapterMatch = matchRoute("/v1/chapter/:osis/:ch", path);
      if (chapterMatch) return await handleChapter({ ...params, params: chapterMatch });

      const bookMatch = matchRoute("/v1/book/:osis", path);
      if (bookMatch) return await handleBook({ ...params, params: bookMatch });

      const crossrefsMatch = matchRoute("/v1/crossrefs/:osisRef", path);
      if (crossrefsMatch) return await handleCrossrefs({ ...params, params: crossrefsMatch });

      const passageMatch = matchRoute("/v1/passage/:ref", path);
      if (passageMatch) return await handlePassage({ ...params, params: passageMatch });

      const resolveMatch = matchRoute("/v1/resolve/:input", path);
      if (resolveMatch) return await handleResolve({ ...params, params: resolveMatch });

      // Unknown path under /v1/ -> 404. Anything else -> 404 with a hint.
      return errorResponse(404, `Not found: ${path}`, { origin: "edge" });
    } catch (err) {
      // Never leak internal stack traces; return a clean 502 with CORS headers.
      const message = err && err.message ? err.message : "Internal Worker error.";
      return errorResponse(502, `Worker error: ${message}`, { origin: "edge" });
    }
  },
};

// Minimal path-to-params matcher. Supports `:param` segments. `:ref` and
// `:input` are "catch-all" (match the remainder of the path including
// slashes) so that references like "John 3:16-18" and resolve inputs like
// "https://www.bible.com/bible/111/JHN.3.16" can include URL-encoded
// slashes/spaces.
//
// Returns { param: value, ... } on match, or null.
function matchRoute(pattern, path) {
  // Catch-all param names: everything after this token becomes the value.
  const CATCH_ALL_PARAMS = [":ref", ":input"];
  const catchAll = CATCH_ALL_PARAMS.find((p) => pattern.includes("/" + p));
  if (!catchAll) {
    // Standard :param matching (no slashes in param values).
    const pp = pattern.split("/").filter(Boolean);
    const ap = path.split("/").filter(Boolean);
    if (pp.length !== ap.length) return null;
    const params = {};
    for (let i = 0; i < pp.length; i++) {
      if (pp[i].startsWith(":")) {
        const key = pp[i].slice(1);
        // Decode each standard param (crossrefs/GEN.1.1, book/GEN, etc.).
        try {
          params[key] = decodeURIComponent(ap[i]);
        } catch {
          params[key] = ap[i];
        }
      } else if (pp[i] !== ap[i]) {
        return null;
      }
    }
    return params;
  }

  // Catch-all matching: pattern prefix must match, then everything after
  // becomes the value of the catch-all param.
  const key = catchAll.slice(1);
  const prefix = pattern.split("/" + catchAll)[0];
  if (!path.startsWith(prefix + "/")) return null;
  const remainder = path.slice(prefix.length + 1);
  try {
    return { [key]: decodeURIComponent(remainder) };
  } catch {
    return { [key]: remainder };
  }
}
