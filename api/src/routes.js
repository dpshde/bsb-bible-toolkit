// Route handlers for each BSB API endpoint.
//
// Each handler receives:
//   { params, url, env, ctx, booksCache }
// where `booksCache` is a memoized map of OSIS -> book metadata parsed from
// v1/books.json on first use, shared across requests within the same Worker
// isolate. Handlers return a Response object (already including CORS, X-Origin,
// and Cache-Control headers as appropriate).

import { fetchCached } from "./cache.js";
import { jsonResponse, errorResponse, IMMUTABLE_CACHE, VALID_SOURCES, TRANSLATION_ID, TRANSLATION_NAME } from "./respond.js";
import { parsePassageInput } from "./passage.js";
import { parseResolveInput } from "./resolve.js";
import { getVerseCount, isOsisBookCode, OSIS_BOOK_ORDER, OSIS_BOOK_CODES } from "grab-bcv";

const OSIS_RE = /^[A-Z0-9]{2,3}$/;
const OSIS_REF_RE = /^[A-Z0-9]{2,3}\.\d+\.\d+$/;

// Serve v1/books.json (the catalog) with edge/R2/Arweave fallback.
export async function handleBooks({ env, ctx }) {
  const result = await fetchCached({ key: "v1/books.json", env, ctx });
  if (!result.ok) return errorResponse(result.status, result.error, { origin: "r2" });
  const books = safeParse(result.body);
  if (!Array.isArray(books)) return errorResponse(502, "Book catalog is malformed.", { origin: result.origin });
  return jsonResponse(books, { origin: result.origin, cacheControl: IMMUTABLE_CACHE });
}

// GET /v1/book/:osis  -> v1/book/<OSIS>.json
export async function handleBook({ params, env, ctx }) {
  const osis = (params.osis || "").toUpperCase();
  if (!OSIS_RE.test(osis) || !isOsisBookCode(osis)) {
    return errorResponse(404, `Unknown book OSIS code: ${params.osis || "(empty)"}`, { origin: "r2" });
  }
  const result = await fetchCached({ key: `v1/book/${osis}.json`, env, ctx });
  if (!result.ok) {
    if (result.status === 503) return errorResponse(503, result.error, { origin: "r2" });
    return errorResponse(404, `Book not found: ${osis}`, { origin: "r2" });
  }
  return new Response(result.body, {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "X-Origin": result.origin,
      "Cache-Control": IMMUTABLE_CACHE,
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    },
  });
}

// GET /v1/chapter/:osis/:ch  -> v1/chapter/<OSIS>/<N>.json
export async function handleChapter({ params, env, ctx }) {
  const osis = (params.osis || "").toUpperCase();
  const chStr = params.ch || "";
  const ch = Number.parseInt(chStr, 10);

  if (!OSIS_RE.test(osis) || !isOsisBookCode(osis)) {
    return errorResponse(404, `Unknown book OSIS code: ${params.osis || "(empty)"}`, { origin: "r2" });
  }
  if (!/^\d+$/.test(chStr) || !Number.isInteger(ch) || ch < 1) {
    return errorResponse(404, `Invalid chapter number: ${chStr}`, { origin: "r2" });
  }
  // Use grab-bcv to validate chapter range. A null verse count means the chapter
  // does not exist in the canon, which is a 404 (not a 400).
  if (getVerseCount(osis, ch) === null) {
    return errorResponse(404, `Chapter ${ch} does not exist in ${osis}.`, { origin: "r2" });
  }

  const result = await fetchCached({ key: `v1/chapter/${osis}/${ch}.json`, env, ctx });
  if (!result.ok) {
    if (result.status === 503) return errorResponse(503, result.error, { origin: "r2" });
    return errorResponse(404, `Chapter not found: ${osis} ${ch}`, { origin: "r2" });
  }
  return new Response(result.body, {
    status: 200,
    headers: withContentHeaders(result.origin, IMMUTABLE_CACHE),
  });
}

// GET /v1/verse/:osisRef  -> v1/verse/<OSISRef>.json
export async function handleVerse({ params, env, ctx }) {
  const osisRef = (params.osisRef || "").toUpperCase();

  // Validate OSIS ref format: BOOK.CHAPTER.VERSE with integer components.
  if (!OSIS_REF_RE.test(osisRef)) {
    return errorResponse(404, `Invalid verse reference: ${params.osisRef || "(empty)"}`, { origin: "r2" });
  }
  const [book, chStr, vStr] = osisRef.split(".");
  if (!isOsisBookCode(book)) {
    return errorResponse(404, `Unknown book OSIS code: ${book}`, { origin: "r2" });
  }
  const ch = Number.parseInt(chStr, 10);
  const v = Number.parseInt(vStr, 10);
  const maxV = getVerseCount(book, ch);
  if (maxV === null) {
    return errorResponse(404, `Chapter ${ch} does not exist in ${book}.`, { origin: "r2" });
  }
  if (v < 1 || v > maxV) {
    return errorResponse(404, `Verse ${osisRef} does not exist.`, { origin: "r2" });
  }

  const result = await fetchCached({ key: `v1/verse/${osisRef}.json`, env, ctx });
  if (!result.ok) {
    if (result.status === 503) return errorResponse(503, result.error, { origin: "r2" });
    return errorResponse(404, `Verse not found: ${osisRef}`, { origin: "r2" });
  }
  return new Response(result.body, {
    status: 200,
    headers: withContentHeaders(result.origin, IMMUTABLE_CACHE),
  });
}

// GET /v1/passage/:ref  -> parse via grab-bcv, expand range, fetch each verse, compose.
export async function handlePassage({ params, env, ctx }) {
  // params.ref is URL-decoded by the router. Whitespace-only refs are 400
  // (VAL-API-041). Unparseable / unknown refs are 404 (VAL-API-015).
  const raw = decodeURIComponent(params.ref || "");
  if (raw.trim() === "") {
    return errorResponse(400, "Passage reference is empty.", { origin: "r2" });
  }

  const parsed = parsePassageInput(raw);
  if (!parsed.ok) {
    return errorResponse(parsed.status, parsed.error, { origin: "r2" });
  }

  const refs = parsed.refs;
  const verses = [];
  const skipped = [];
  let worstOrigin = "edge"; // pick the "lowest" tier actually used to satisfy the request
  const originRank = { edge: 0, r2: 1, arweave: 2 };
  let tierExhaustionCount = 0;

  for (const ref of refs) {
    const r = await fetchCached({ key: `v1/verse/${ref}.json`, env, ctx });
    if (!r.ok) {
      if (r.status === 503) {
        // Tier exhaustion: count it. We may be facing either a real outage
        // (every verse 503s) or a canonical gap where the verse simply does
        // not exist in the dataset (e.g. MAT.17.21, MAT.18.11, MAT.23.14).
        // If the rest of the range resolves, we treat 503s as gaps; if every
        // verse 503s, we surface the outage as 503.
        tierExhaustionCount++;
        skipped.push(ref);
        continue;
      }
      // Any other miss status: canonical gap, skip silently.
      skipped.push(ref);
      continue;
    }
    const verseObj = safeParse(r.body);
    if (verseObj && typeof verseObj === "object") verses.push(verseObj);
    if (originRank[r.origin] > originRank[worstOrigin]) worstOrigin = r.origin;
  }

  // If every verse in the range hit tier exhaustion, the data is genuinely
  // unavailable; surface 503 to the client.
  if (verses.length === 0 && tierExhaustionCount > 0) {
    return errorResponse(503, `Content unavailable for passage: ${raw}`, { origin: "r2" });
  }

  // If no verses survived but nothing went 503 (range fully outside canon),
  // return 404.
  if (verses.length === 0) {
    return errorResponse(404, `No verses found for passage: ${raw}`, { origin: "r2" });
  }

  return jsonResponse(
    {
      translation: TRANSLATION_ID,
      ref: parsed.parsed.canonical,
      display: parsed.display,
      rangeType: parsed.parsed.rangeType,
      start: parsed.parsed.start,
      end: parsed.parsed.end,
      verseCount: verses.length,
      verses,
      ...(skipped.length > 0 ? { skipped } : {}),
    },
    { origin: worstOrigin, cacheControl: IMMUTABLE_CACHE },
  );
}

// GET /v1/resolve/:input  -> parse ANY input format via grab-bcv, expand range,
// fetch each verse, compose. Accepts human refs, OSIS strings, Bible app URIs
// (Logos/Accordance), and provider URLs (Bible.com/Bible Gateway). Returns the
// same verse objects as /v1/passage, plus originalInput and canonical.
export async function handleResolve({ params, env, ctx }) {
  // params.input is the catch-all remainder after "/v1/resolve/". It is
  // URL-decoded by the router. Whitespace-only or empty input is 400
  // (VAL-RESOLVE-017). Unparseable non-empty input is also 400. Books outside
  // the BSB canon that grab-bcv rejects surface as 400 (or 404 when grab-bcv
  // recognizes the book but it is absent from the dataset).
  const originalInput = decodeURIComponent(params.input || "");
  if (originalInput.trim() === "") {
    return errorResponse(400, "Resolve input is empty.", { origin: "r2" });
  }

  const parsed = parseResolveInput(originalInput);
  if (!parsed.ok) {
    return errorResponse(parsed.status, parsed.error, { origin: "r2" });
  }

  const refs = parsed.refs;
  const verses = [];
  const skipped = [];
  let worstOrigin = "edge";
  const originRank = { edge: 0, r2: 1, arweave: 2 };
  let tierExhaustionCount = 0;

  for (const ref of refs) {
    const r = await fetchCached({ key: `v1/verse/${ref}.json`, env, ctx });
    if (!r.ok) {
      if (r.status === 503) {
        tierExhaustionCount++;
        skipped.push(ref);
        continue;
      }
      skipped.push(ref);
      continue;
    }
    const verseObj = safeParse(r.body);
    if (verseObj && typeof verseObj === "object") verses.push(verseObj);
    if (originRank[r.origin] > originRank[worstOrigin]) worstOrigin = r.origin;
  }

  if (verses.length === 0 && tierExhaustionCount > 0) {
    return errorResponse(503, `Content unavailable for input: ${originalInput}`, { origin: "r2" });
  }
  if (verses.length === 0) {
    return errorResponse(404, `No verses found for input: ${originalInput}`, { origin: "r2" });
  }

  return jsonResponse(
    {
      translation: TRANSLATION_ID,
      originalInput,
      canonical: parsed.canonical,
      passage: parsed.display,
      ref: parsed.canonical,
      display: parsed.display,
      rangeType: parsed.parsed.rangeType,
      start: parsed.parsed.start,
      end: parsed.parsed.end,
      verseCount: verses.length,
      verses,
      ...(skipped.length > 0 ? { skipped } : {}),
    },
    { origin: worstOrigin, cacheControl: IMMUTABLE_CACHE },
  );
}

// GET /v1/search?q=...  -> scan v1/search-index.json for substring matches.
export async function handleSearch({ url, env, ctx }) {
  const q = (url.searchParams.get("q") || "").trim();
  if (!q) {
    return errorResponse(400, "Missing required query parameter: q", { origin: "r2" });
  }
  const needle = q.toLowerCase();
  const result = await fetchCached({ key: "v1/search-index.json", env, ctx });
  if (!result.ok) {
    if (result.status === 503) return errorResponse(503, result.error, { origin: "r2" });
    return errorResponse(502, "Search index unavailable.", { origin: "r2" });
  }
  const index = safeParse(result.body);
  if (!Array.isArray(index)) return errorResponse(502, "Search index is malformed.", { origin: result.origin });

  const matches = [];
  for (const entry of index) {
    if (entry && typeof entry.text === "string" && entry.text.toLowerCase().includes(needle)) {
      matches.push({ ref: entry.ref, text: entry.text });
    }
  }

  return jsonResponse(
    {
      translation: TRANSLATION_ID,
      query: q,
      count: matches.length,
      results: matches,
    },
    { origin: result.origin, cacheControl: null },
  );
}

// GET /v1/crossrefs/:osisRef[?source=...]  -> v1/crossrefs/<OSISRef>.json with optional filter.
export async function handleCrossrefs({ params, url, env, ctx }) {
  const osisRef = (params.osisRef || "").toUpperCase();
  if (!OSIS_REF_RE.test(osisRef)) {
    return errorResponse(404, `Invalid verse reference: ${params.osisRef || "(empty)"}`, { origin: "r2" });
  }
  const [book, chStr, vStr] = osisRef.split(".");
  if (!isOsisBookCode(book)) {
    return errorResponse(404, `Unknown book OSIS code: ${book}`, { origin: "r2" });
  }
  const maxV = getVerseCount(book, Number.parseInt(chStr, 10));
  if (maxV === null) {
    return errorResponse(404, `Chapter ${chStr} does not exist in ${book}.`, { origin: "r2" });
  }
  if (Number.parseInt(vStr, 10) < 1 || Number.parseInt(vStr, 10) > maxV) {
    return errorResponse(404, `Verse ${osisRef} does not exist.`, { origin: "r2" });
  }

  const result = await fetchCached({ key: `v1/crossrefs/${osisRef}.json`, env, ctx });
  if (!result.ok) {
    if (result.status === 503) return errorResponse(503, result.error, { origin: "r2" });
    return errorResponse(404, `Cross-references not found for: ${osisRef}`, { origin: "r2" });
  }
  const data = safeParse(result.body) || {};

  // Source filtering. `?source=` is repeatable. Values are case-insensitive.
  // Empty value means "no filter" (return all). Unknown values silently filter
  // the result to an empty array (VAL-API-022, VAL-API-045). A valid source
  // combined with an invalid one keeps only the valid matches (VAL-API-044).
  const rawSources = url.searchParams.getAll("source");
  let crossReferences = Array.isArray(data.crossReferences) ? data.crossReferences : [];
  let entityLinks = Array.isArray(data.entityLinks) ? data.entityLinks : [];

  if (rawSources.length > 0) {
    // Treat empty-string values as "no filter".
    const nonEmpty = rawSources.filter((s) => s !== "");
    if (nonEmpty.length > 0) {
      const lowered = new Set(nonEmpty.map((s) => s.toLowerCase()));
      crossReferences = crossReferences.filter((xr) => xr && typeof xr.source === "string" && lowered.has(xr.source.toLowerCase()));
      entityLinks = entityLinks.filter((el) => el && typeof el.source === "string" && lowered.has(el.source.toLowerCase()));
    }
  }

  return jsonResponse(
    {
      translation: TRANSLATION_ID,
      ref: data.ref || osisRef,
      crossReferences,
      entityLinks,
    },
    { origin: result.origin, cacheControl: null },
  );
}

// GET /v1/health -> service status + version + cache tier availability.
export async function handleHealth({ env }) {
  const version = (env && env.WORKER_VERSION) || "1.0.0";
  return jsonResponse(
    {
      status: "ok",
      translation: TRANSLATION_ID,
      translationName: TRANSLATION_NAME,
      version,
      cache: {
        edge: true,
        r2: Boolean(env && env.BSB_DATASET),
        arweave: Boolean(env && env.ARWEAVE_ORIGIN),
      },
      arweaveOrigin: env && env.ARWEAVE_ORIGIN ? env.ARWEAVE_ORIGIN : null,
    },
    { origin: "edge", cacheControl: "no-store" },
  );
}

// ---- Helpers ----

function safeParse(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function withContentHeaders(origin, cacheControl) {
  return {
    "Content-Type": "application/json; charset=utf-8",
    "X-Origin": origin,
    "Cache-Control": cacheControl,
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

// Re-export for tests and external consumers.
export { VALID_SOURCES, OSIS_BOOK_ORDER, OSIS_BOOK_CODES };
