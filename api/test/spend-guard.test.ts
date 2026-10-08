// Spend-guard tests: passage/resolve verse cap and the Workers rate limiter.
// Cap checks are pure (grab-bcv expansion, no R2). The 429 check uses the
// RATE_LIMITER binding from wrangler.toml on a dedicated client key so it
// does not consume the shared bucket the rest of the suite uses.

import { describe, test, expect } from "vitest";
import { env, SELF } from "cloudflare:test";
import { getVerseCount } from "grab-bcv";
import {
  MAX_PASSAGE_VERSES,
  parsePassageInput,
  passageCapError,
} from "../src/passage.js";
import { parseResolveInput } from "../src/resolve.js";
import {
  RATE_LIMIT_PERIOD_SECONDS,
  RATE_LIMIT_REQUESTS,
  clientRateLimitKey,
  enforceRateLimit,
} from "../src/rate-limit.js";
import { fetchJson } from "./setup";

function genesisEndForCount(count: number): string {
  let seen = 0;
  for (let chapter = 1; chapter <= 50; chapter++) {
    const total = getVerseCount("GEN", chapter);
    if (!total) break;
    if (seen + total >= count) {
      return `GEN.${chapter}.${count - seen}`;
    }
    seen += total;
  }
  throw new Error(`Genesis has fewer than ${count} verses`);
}

describe("passage verse cap", () => {
  test("MAX_PASSAGE_VERSES is a fixed product cap above Psalm 119", () => {
    expect(MAX_PASSAGE_VERSES).toBe(250);
    const psalm119 = parsePassageInput("PSA.119.1-PSA.119.176");
    expect(psalm119.ok).toBe(true);
    if (psalm119.ok) expect(psalm119.refs.length).toBe(176);
    expect(176).toBeLessThan(MAX_PASSAGE_VERSES);
  });

  test("allows exactly 250 verses and rejects 251", () => {
    const atCap = parsePassageInput(`GEN.1.1-${genesisEndForCount(MAX_PASSAGE_VERSES)}`);
    expect(atCap.ok).toBe(true);
    if (atCap.ok) expect(atCap.refs.length).toBe(MAX_PASSAGE_VERSES);

    const over = parsePassageInput(`GEN.1.1-${genesisEndForCount(MAX_PASSAGE_VERSES + 1)}`);
    expect(over.ok).toBe(false);
    if (!over.ok) {
      expect(over.status).toBe(400);
      expect(over.error).toBe(passageCapError());
    }
  });

  test("whole-Bible passage and resolve inputs are rejected before expansion is returned", () => {
    const passage = parsePassageInput("GEN.1.1-REV.22.21");
    expect(passage.ok).toBe(false);
    if (!passage.ok) expect(passage.status).toBe(400);

    const resolved = parseResolveInput("Genesis 1:1-Revelation 22:21");
    expect(resolved.ok).toBe(false);
    if (!resolved.ok) expect(resolved.status).toBe(400);
  });

  test("a short cross-book range still expands", () => {
    const parsed = parsePassageInput("MAT.28.20-MRK.1.1");
    expect(parsed.ok).toBe(true);
    if (parsed.ok) expect(parsed.refs).toEqual(["MAT.28.20", "MRK.1.1"]);
  });

  test("GET /v1/passage and /v1/resolve return 400 for a whole-Bible range", async () => {
    const passage = await fetchJson(SELF, "/v1/passage/GEN.1.1-REV.22.21");
    expect(passage.res.status).toBe(400);
    expect(passage.body.error).toContain(String(MAX_PASSAGE_VERSES));
    expect(passage.body.verses).toBeUndefined();

    const resolved = await fetchJson(
      SELF,
      "/v1/resolve/Genesis%201:1-Revelation%2022:21",
    );
    expect(resolved.res.status).toBe(400);
    expect(resolved.body.error).toContain(String(MAX_PASSAGE_VERSES));
    expect(resolved.body.verses).toBeUndefined();
  });
});

describe("rate limit", () => {
  test("client key is the trimmed connecting IP, else unknown", () => {
    const withIp = new Request("https://bsb-api.test/v1/health", {
      headers: { "CF-Connecting-IP": "  203.0.113.10  " },
    });
    expect(clientRateLimitKey(withIp)).toBe("203.0.113.10");

    const missing = new Request("https://bsb-api.test/v1/health");
    expect(clientRateLimitKey(missing)).toBe("unknown");

    const longIp = "x".repeat(200);
    const huge = new Request("https://bsb-api.test/v1/health", {
      headers: { "CF-Connecting-IP": longIp },
    });
    expect(clientRateLimitKey(huge).length).toBe(128);
  });

  test("enforceRateLimit returns 429 with Retry-After when the binding denies", async () => {
    const request = new Request("https://bsb-api.test/v1/books", {
      headers: { "CF-Connecting-IP": "203.0.113.20" },
    });
    const seen: string[] = [];
    const denied = await enforceRateLimit(request, {
      RATE_LIMITER: {
        async limit({ key }: { key: string }) {
          seen.push(key);
          return { success: false };
        },
      },
    });
    expect(seen).toEqual(["203.0.113.20"]);
    expect(denied).not.toBeNull();
    expect(denied!.status).toBe(429);
    expect(denied!.headers.get("Retry-After")).toBe(String(RATE_LIMIT_PERIOD_SECONDS));
    expect(denied!.headers.get("Cache-Control")).toBe("no-store");
    expect(denied!.headers.get("Access-Control-Allow-Origin")).toBe("*");
    const body = await denied!.json();
    expect(body.error).toBeTruthy();
    expect(body.status).toBe(429);
  });

  test("enforceRateLimit allows the request when the binding accepts", async () => {
    const request = new Request("https://bsb-api.test/v1/health", {
      headers: { "CF-Connecting-IP": "203.0.113.21" },
    });
    const allowed = await enforceRateLimit(request, {
      RATE_LIMITER: {
        async limit() {
          return { success: true };
        },
      },
    });
    expect(allowed).toBeNull();
  });

  test("RATE_LIMITER binding is present and returns 429 after the configured limit", async () => {
    expect(RATE_LIMIT_REQUESTS).toBe(100);
    expect(RATE_LIMIT_PERIOD_SECONDS).toBe(60);
    const limiter = (env as any).RATE_LIMITER;
    expect(limiter).toBeTruthy();
    expect(typeof limiter.limit).toBe("function");

    const headers = { "CF-Connecting-IP": "203.0.113.44" };
    const key = clientRateLimitKey(
      new Request("https://bsb-api.test/v1/health", { headers }),
    );
    for (let i = 0; i < RATE_LIMIT_REQUESTS; i++) {
      const result = await limiter.limit({ key });
      expect(result.success).toBe(true);
    }

    const { res, body } = await fetchJson(SELF, "/v1/health", { headers });
    expect(res.status).toBe(429);
    expect(res.headers.get("Retry-After")).toBe("60");
    expect(body.status).toBe(429);

    const under = await fetchJson(SELF, "/v1/health", {
      headers: { "CF-Connecting-IP": "203.0.113.45" },
    });
    expect(under.res.status).toBe(200);
  });

  test("OPTIONS preflight is not rate limited", async () => {
    const headers = { "CF-Connecting-IP": "203.0.113.44" };
    const { res } = await fetchJson(SELF, "/v1/health", { method: "OPTIONS", headers });
    expect([200, 204]).toContain(res.status);
    expect(res.headers.get("Retry-After")).toBeNull();
  });
});
