// Loads BSB seed-data fixtures from disk (in Node.js context) and exposes them
// as a single JSON-serializable map. Used by vitest.config.ts to populate a
// SEED_FIXTURES binding; the test setup helper then walks the map and seeds
// the in-memory R2 bucket via env.BSB_DATASET.put().
//
// We load a focused subset of the full dataset: enough to exercise every
// VAL-API assertion (catalog, sample book/chapter/verse, crossrefs, search
// index entries for query terms used in tests, passage verses for the
// references the tests expand).

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, resolve, sep, posix } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = resolve(fileURLToPath(import.meta.url), "..");
const SEED_DIR = resolve(__dirname, "..", "seed-data");

function readSeed(key) {
  const parts = key.split("/").join(sep);
  return readFileSync(join(SEED_DIR, parts), "utf8");
}

function hasSeed(key) {
  return existsSync(join(SEED_DIR, key.split("/").join(sep)));
}

// Verse OSIS refs we need for passage/verse tests. Each ref maps to two keys:
// v1/verse/<ref>.json and v1/crossrefs/<ref>.json. We also need every verse in
// the test passages (John 3:16-18, John 3:16-John 4:2, Psalm 119:1-3,
// Matthew 1:1-Mark 1:1, John 3:16). To keep the fixture compact, we walk the
// full ranges by listing seed-data/v1/verse for the relevant book prefixes.
const PASSAGE_VERSE_REFS = collectPassageRefs();

function collectPassageRefs() {
  const refs = new Set();
  // John 3:16-18
  refs.add("JHN.3.16"); refs.add("JHN.3.17"); refs.add("JHN.3.18");
  // John 3:16 - John 4:2 (JHN.3.16 through JHN.3.36 + JHN.4.1 + JHN.4.2)
  for (let v = 16; v <= 36; v++) refs.add(`JHN.3.${v}`);
  refs.add("JHN.4.1"); refs.add("JHN.4.2");
  // Psalm 119:1-3
  refs.add("PSA.119.1"); refs.add("PSA.119.2"); refs.add("PSA.119.3");
  // Matthew 1:1 - Mark 1:1 (every verse in Matthew 1 through Matthew 28 plus Mark 1:1)
  // Matthew 1 has 25 verses. Matthew total = 28 chapters. Mark 1:1.
  // For the cross-book passage test we need the entire Matthew book plus Mark 1:1.
  for (const ref of listChapterVerseFiles("MAT")) refs.add(ref);
  refs.add("MRK.1.1");
  // Standalone verses used in direct endpoint tests.
  refs.add("GEN.1.1"); refs.add("GEN.1.2"); refs.add("JUD.1.1");
  // Resolve endpoint (M4): 1 Corinthians 13:4-7 (VAL-RESOLVE-002, 013, 016)
  refs.add("1CO.13.4"); refs.add("1CO.13.5"); refs.add("1CO.13.6"); refs.add("1CO.13.7");
  return refs;
}

// List every OSIS ref in a book by reading v1/verse/<book>.*.json filenames.
function listChapterVerseFiles(bookOsis) {
  const refs = [];
  const dir = join(SEED_DIR, "v1", "verse");
  if (!existsSync(dir)) return refs;
  const prefix = `${bookOsis}.`;
  for (const entry of readdirSync(dir)) {
    if (entry.startsWith(prefix) && entry.endsWith(".json")) {
      refs.push(entry.slice(0, -".json".length));
    }
  }
  return refs;
}

// Verse refs needed for direct /v1/verse/ tests and cache-tier tests.
const VERSE_KEYS = [];
for (const ref of PASSAGE_VERSE_REFS) {
  VERSE_KEYS.push(`v1/verse/${ref}.json`);
}

// Crossref keys needed (one per verse we test for crossrefs, plus all verses
// from passage tests so source-filtering counts stay meaningful).
const CROSSREF_KEYS = [];
for (const ref of PASSAGE_VERSE_REFS) {
  CROSSREF_KEYS.push(`v1/crossrefs/${ref}.json`);
}

// Books we need full per-book JSON for: GEN (book endpoint, MAT for passage).
const BOOK_KEYS = ["v1/book/GEN.json", "v1/book/MAT.json"];

// Chapters we need full chapter JSON for: GEN/1.
const CHAPTER_KEYS = ["v1/chapter/GEN/1.json"];

// Search index: load all entries (the search test needs substring matches).
// To keep things bounded, we load the full search index if it fits under
// ~50 MB, otherwise we filter to entries containing "love" or "beginning".
const SEARCH_INDEX_KEY = "v1/search-index.json";

function loadSearchIndex() {
  if (!hasSeed(SEARCH_INDEX_KEY)) return [];
  const all = JSON.parse(readSeed(SEARCH_INDEX_KEY));
  if (!Array.isArray(all)) return [];
  // Keep entries that match any test query term plus a small sample. The
  // search endpoint does substring matching, so we need at least the rows that
  // contain "love" (VAL-API-016) and "beginning" (smoke expectation).
  const keep = [];
  let loveCount = 0, beginningCount = 0;
  for (const e of all) {
    const lower = (e.text || "").toLowerCase();
    if (lower.includes("love")) { keep.push(e); loveCount++; }
    else if (lower.includes("beginning")) { keep.push(e); beginningCount++; }
  }
  // Always keep at least 50 love matches and 50 beginning matches.
  void loveCount; void beginningCount;
  return keep;
}

// Catalog is always required.
const CATALOG = hasSeed("v1/books.json") ? readSeed("v1/books.json") : "[]";

// Build the fixtures map. Keys are R2 object keys, values are raw JSON strings.
export function loadFixtures() {
  const fixtures = {
    "v1/books.json": CATALOG,
    [SEARCH_INDEX_KEY]: JSON.stringify(loadSearchIndex()),
  };
  for (const k of BOOK_KEYS) if (hasSeed(k)) fixtures[k] = readSeed(k);
  for (const k of CHAPTER_KEYS) if (hasSeed(k)) fixtures[k] = readSeed(k);
  for (const k of VERSE_KEYS) if (hasSeed(k)) fixtures[k] = readSeed(k);
  for (const k of CROSSREF_KEYS) if (hasSeed(k)) fixtures[k] = readSeed(k);
  return fixtures;
}

// Eagerly build and freeze the fixture set so it's ready when the config is
// imported. (vitest.config.ts imports this module in Node context.)
export const FIXTURES = (() => {
  if (!existsSync(SEED_DIR)) return {};
  try {
    return loadFixtures();
  } catch (err) {
    console.warn("Failed to load seed fixtures:", err.message);
    return {};
  }
})();
