// 4-tier cache-aside fetcher for BSB JSON content.
//
// Tier 1 (Edge Cache API): per-PoP volatile cache via `caches.default`.
//   HIT  -> return { body, origin: "edge" }
// Tier 2 (R2 bucket):       persistent cloud cache via `env.BSB_DATASET`.
//   HIT  -> warm edge cache, return { body, origin: "r2" }
// Tier 3 (Arweave gateway): canonical permanent origin via HTTP fetch.
//   HIT  -> warm R2 + edge, return { body, origin: "arweave" }
// Tier 4 (503):             all tiers exhausted; caller returns 503.
//
// `key` is the R2 object key (e.g. "v1/verse/GEN.1.1.json").
// The cache key for the edge cache and Arweave URL both derive from `key`.
//
// All cache-warming side effects are best-effort. They MUST NOT propagate
// exceptions to the caller; a failure to warm a tier is not a request failure.

const RE_VALID_KEY = /^v1\/[A-Za-z0-9._\-\/]+\.json$/;

const DEFAULT_ARWEAVE_ORIGIN = "https://api_bsb.scripture.ar-io.dev";

export async function fetchCached({ key, env, ctx }) {
  if (!RE_VALID_KEY.test(key)) {
    return { ok: false, status: 400, error: `Invalid cache key: ${key}` };
  }

  const cacheUrl = new URL(`https://bsb-cache.local/${key}`);
  const cache = typeof caches !== "undefined" ? caches.default : null;

  // --- Tier 1: Edge Cache API ---
  if (cache) {
    try {
      const cached = await cache.match(cacheUrl);
      if (cached && cached.body) {
        const text = await cached.text();
        if (text) return { ok: true, body: text, origin: "edge" };
      }
    } catch {
      // Edge cache read failed; fall through to R2.
    }
  }

  // --- Tier 2: R2 bucket ---
  if (env && env.BSB_DATASET && typeof env.BSB_DATASET.get === "function") {
    try {
      const obj = await env.BSB_DATASET.get(key);
      if (obj && obj.body) {
        const text = await obj.text();
        if (text) {
          // Warm edge cache (best effort; never blocks the response).
          scheduleWarm(() => warmEdge(cache, cacheUrl, text), ctx);
          return { ok: true, body: text, origin: "r2" };
        }
      }
    } catch {
      // R2 read failed; fall through to Arweave.
    }
  }

  // --- Tier 3: Arweave gateway ---
  // Skip the network fetch entirely if the origin is obviously unreachable
  // (e.g. when running locally with a placeholder host). This avoids
  // generating noisy workerd DNS errors during tests/local dev.
  const origin =
    env && env.ARWEAVE_ORIGIN ? env.ARWEAVE_ORIGIN : DEFAULT_ARWEAVE_ORIGIN;
  if (origin && !/\.(invalid|example|test|localhost)$/i.test(origin)) {
    const arweaveUrl = `${origin}/${key}`;
    try {
      const resp = await fetch(arweaveUrl, {
        headers: { Accept: "application/json" },
      });
      if (resp.ok) {
        const text = await resp.text();
        if (text) {
          scheduleWarm(() => warmEdge(cache, cacheUrl, text), ctx);
          scheduleWarm(() => warmR2(env, key, text), ctx);
          return { ok: true, body: text, origin: "arweave" };
        }
      }
    } catch {
      // Arweave unreachable; fall through to 503.
    }
  }

  // --- Tier 4: all exhausted ---
  return {
    ok: false,
    status: 503,
    error: `Content unavailable for key ${key} across all cache tiers.`,
  };
}

// Schedule a cache-warming promise. Uses ctx.waitUntil when available so the
// runtime keeps the warming promise alive past the response. Any thrown error
// is swallowed so it can never crash the isolate or fail the request.
function scheduleWarm(promiseFactory, ctx) {
  const p = Promise.resolve()
    .then(promiseFactory)
    .catch(() => {
      /* ignore: warming is best-effort */
    });
  if (ctx && typeof ctx.waitUntil === "function") {
    try {
      ctx.waitUntil(p);
    } catch {
      /* ignore: waitUntil not usable in this runtime */
    }
  }
  return p;
}

// Warm the edge cache with a 200 response carrying immutable cache headers.
async function warmEdge(cache, cacheUrl, body) {
  if (!cache || !body) return;
  const warmResp = new Response(body, {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "public, max-age=31536000, immutable",
    },
  });
  await cache.put(cacheUrl, warmResp);
}

// Warm the R2 bucket. No-op if the binding is absent or read-only (some
// Miniflare test setups expose R2 without write support).
async function warmR2(env, key, body) {
  if (!env || !env.BSB_DATASET) return;
  if (typeof env.BSB_DATASET.put !== "function") return;
  await env.BSB_DATASET.put(key, body);
}
