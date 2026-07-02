// Converts output/dataset/ files into the v1/ R2 key structure consumed by the Worker.
//
// The source dataset layout (produced by src/bsb_pdf_toolkit/build_dataset.py) is:
//   output/dataset/bsb-dataset.json
//   output/dataset/manifest.json
//   output/dataset/cross-refs.json
//   output/dataset/entity-links.json
//   output/dataset/books/<OSIS>.json
//   output/dataset/books/<OSIS>/chapters/<N>.json
//   output/dataset/books/<OSIS>/verses/<OSIS>.<C>.<V>.json
//
// The R2 key structure (served by the Worker) is:
//   v1/books.json                 -> book catalog (array of 66 book metadata objects)
//   v1/book/<OSIS>.json           -> full book object
//   v1/chapter/<OSIS>/<N>.json    -> full chapter object
//   v1/verse/<OSISRef>.json       -> single verse object
//   v1/crossrefs/<OSISRef>.json   -> per-verse cross-references (with entity links merged in)
//   v1/search-index.json          -> compact search index: [{ ref, text }, ...]
//
// Usage:
//   node scripts/seed-r2-local.mjs                # reads ../output/dataset, writes ./seed-data
//   node scripts/seed-r2-local.mjs --in <dir> --out <dir>
//
// This script is filesystem-only. The CI workflow (M3) does the actual R2 upload
// via `wrangler r2 object put`. For local dev/tests, Miniflare reads from the
// output directory declared in vitest.config.ts / wrangler.toml.

import { readFileSync, writeFileSync, mkdirSync, readdirSync, existsSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..", "..");

function parseArgs(argv) {
  const args = { inDir: null, outDir: null };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--in") args.inDir = argv[++i];
    else if (a === "--out") args.outDir = argv[++i];
    else if (a === "--help" || a === "-h") {
      console.log("Usage: seed-r2-local.mjs [--in <dataset-dir>] [--out <seed-dir>]");
      process.exit(0);
    }
  }
  return args;
}

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function writeJson(outDir, key, obj) {
  const full = join(outDir, key);
  mkdirSync(dirname(full), { recursive: true });
  writeFileSync(full, JSON.stringify(obj));
}

function main() {
  const args = parseArgs(process.argv);
  const inDir = args.inDir || join(REPO_ROOT, "output", "dataset");
  const outDir = args.outDir || join(__dirname, "..", "seed-data");

  if (!existsSync(inDir)) {
    console.error(`Dataset directory not found: ${inDir}`);
    console.error("Run the M1 dataset builder first (python -m bsb_pdf_toolkit.build_dataset).");
    process.exit(1);
  }

  console.log(`Seeding R2 key structure from ${inDir} -> ${outDir}`);

  const manifest = readJson(join(inDir, "manifest.json"));
  const crossRefs = readJson(join(inDir, "cross-refs.json"));
  const entityLinks = readJson(join(inDir, "entity-links.json"));

  // 1. v1/books.json -> array of 66 book metadata objects
  //    Worker contract: each book has at least { osis, name, chapters }
  const booksCatalog = manifest.books.map((b) => ({
    osis: b.osis,
    name: b.name,
    chapters: b.chapterCount,
    verses: b.verseCount,
    footnotes: b.footnoteCount,
    crossReferences: b.crossReferenceCount,
  }));
  writeJson(outDir, "v1/books.json", booksCatalog);

  // 2. Group entity links by verseRef for merging into per-verse crossref output.
  const entityLinksByVerse = new Map();
  for (const el of entityLinks) {
    const ref = el.verseRef;
    if (!ref) continue;
    if (!entityLinksByVerse.has(ref)) entityLinksByVerse.set(ref, []);
    entityLinksByVerse.get(ref).push({
      entity: el.entity,
      type: el.type,
      source: el.source,
    });
  }

  let verseFileCount = 0;
  let chapterFileCount = 0;
  let bookFileCount = 0;
  let crossrefFileCount = 0;

  // 3. Walk each book and emit v1/book/<OSIS>.json, v1/chapter/<OSIS>/<N>.json,
  //    v1/verse/<OSISRef>.json, and v1/crossrefs/<OSISRef>.json.
  for (const meta of manifest.books) {
    const osis = meta.osis;
    const bookPath = join(inDir, "books", `${osis}.json`);
    if (!existsSync(bookPath)) {
      console.warn(`Missing per-book file: ${bookPath}`);
      continue;
    }
    const book = readJson(bookPath);

    // Top-level book object (chapters array with verses).
    writeJson(outDir, `v1/book/${osis}.json`, book);
    bookFileCount++;

    for (const ch of book.chapters) {
      const chNum = ch.chapter;

      // v1/chapter/<OSIS>/<N>.json -> { book, bookOsis, chapter, verses: [...] }
      // (matches the per-chapter JSON produced by build_dataset.py)
      const chapterKey = `v1/chapter/${osis}/${chNum}.json`;
      writeJson(outDir, chapterKey, ch);
      chapterFileCount++;

      for (const v of ch.verses) {
        const osisRef = v.osisRef;

        // v1/verse/<OSISRef>.json -> single verse object
        writeJson(outDir, `v1/verse/${osisRef}.json`, v);
        verseFileCount++;

        // v1/crossrefs/<OSISRef>.json -> { ref, crossReferences, entityLinks }
        const base = crossRefs[osisRef] || { crossReferences: [] };
        const entityLinksForVerse = entityLinksByVerse.get(osisRef) || [];
        const crossrefObj = {
          ref: osisRef,
          crossReferences: base.crossReferences || [],
          entityLinks: entityLinksForVerse,
        };
        writeJson(outDir, `v1/crossrefs/${osisRef}.json`, crossrefObj);
        crossrefFileCount++;
      }
    }
  }

  // 4. v1/search-index.json -> compact array of { ref, text }
  //    We rebuild this from the unified dataset for speed and size.
  const unifiedPath = join(inDir, "bsb-dataset.json");
  if (existsSync(unifiedPath)) {
    const unified = readJson(unifiedPath);
    const index = [];
    for (const book of unified.books) {
      for (const ch of book.chapters) {
        for (const v of ch.verses) {
          index.push({ ref: v.osisRef, text: v.text });
        }
      }
    }
    writeJson(outDir, "v1/search-index.json", index);
    console.log(`Wrote search index with ${index.length} entries`);
  } else {
    console.warn(`Missing unified dataset: ${unifiedPath} (search index not built)`);
  }

  console.log(
    `Done. books.json (66), ${bookFileCount} book files, ${chapterFileCount} chapter files, ` +
      `${verseFileCount} verse files, ${crossrefFileCount} crossref files.`,
  );
}

main();
