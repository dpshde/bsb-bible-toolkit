// Test helpers and shared fixtures for the BSB API Worker integration tests.
//
// R2 contents come from a SEED_FIXTURES binding (a JSON-serialized map of
// R2-key -> JSON-string) that vitest.config.ts builds from api/seed-data/ in
// Node.js context. node:fs is NOT available inside the workerd runtime that
// backs the Workers Vitest pool, so we cannot read seed-data/ files directly
// from tests; instead we walk the binding and call env.BSB_DATASET.put() for
// each entry in beforeAll.

import type { R2Bucket } from "@cloudflare/workers-types";

// Canonical set of OSIS codes (used for catalog assertions).
export const EXPECTED_OSIS_CODES = new Set([
  "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA",
  "1KI", "2KI", "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO",
  "ECC", "SNG", "ISA", "JER", "LAM", "EZK", "DAN", "HOS", "JOL", "AMO",
  "OBA", "JON", "MIC", "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL",
  "MAT", "MRK", "LUK", "JHN", "ACT", "ROM", "1CO", "2CO", "GAL", "EPH",
  "PHP", "COL", "1TH", "2TH", "1TI", "2TI", "TIT", "PHM", "HEB", "JAS",
  "1PE", "2PE", "1JN", "2JN", "3JN", "JUD", "REV",
]);

// Type-only declaration so tests can reference env.SEED_FIXTURES without
// importing the cloudflare:test ProvidedEnv augmentation elsewhere.
export interface SeedFixturesEnv {
  SEED_FIXTURES?: string;
  BSB_DATASET?: R2Bucket;
  ARWEAVE_ORIGIN?: string;
  WORKER_VERSION?: string;
}

// Seed an R2 bucket from the SEED_FIXTURES binding. Returns the count of keys
// written. Idempotent: existing keys are overwritten with the same content.
export async function seedR2FromBinding(
  bucket: R2Bucket,
  seedFixturesJson?: string,
): Promise<number> {
  if (!seedFixturesJson) return 0;
  let fixtures: Record<string, string>;
  try {
    fixtures = JSON.parse(seedFixturesJson);
  } catch {
    return 0;
  }
  let count = 0;
  for (const [key, value] of Object.entries(fixtures)) {
    await bucket.put(key, value);
    count++;
  }
  return count;
}

// Fetch helper: invoke a Worker via the SELF fetcher (or a plain fetch
// function) and return the response, parsed JSON body, and raw text.
export async function fetchJson(
  fetcher: { fetch: typeof fetch } | typeof fetch,
  path: string,
  init?: RequestInit,
) {
  const url = new URL(path, "http://bsb-api.test");
  const res =
    typeof fetcher === "function"
      ? await (fetcher as typeof fetch)(url, init)
      : await fetcher.fetch(url, init);
  let body: any = null;
  const text = await res.text();
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  return { res, body, text };
}
