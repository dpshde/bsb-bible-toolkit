// BSB JSON API quickstart for JavaScript / browser / Node.js 18+.
//
// Demonstrates fetching a verse, a chapter, a passage, and filtered
// cross-references from the BSB JSON API. Uses only the global `fetch`, so it
// runs in modern browsers and Node.js 18+ without any npm install.
//
// Browser: open this file's directory and serve it, or copy the functions into
// a module. Node.js: `node javascript_fetch.js` (Node 18+ has global fetch).
//
// Override the API base with the `BSB_API_BASE` environment variable
// (defaults to http://localhost:8787, the local wrangler dev server).

const DEFAULT_BASE = "http://localhost:8787";
const apiBase = (typeof process !== "undefined" && process.env && process.env.BSB_API_BASE) || DEFAULT_BASE;

async function getJson(path, params) {
  const url = new URL(path, apiBase);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (Array.isArray(value)) {
        for (const v of value) url.searchParams.append(key, v);
      } else {
        url.searchParams.set(key, value);
      }
    }
  }
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`API error ${response.status} for ${url.pathname}: ${detail}`);
  }
  return response.json();
}

async function showVerse(osisRef) {
  const verse = await getJson(`/v1/verse/${osisRef}`);
  console.log(`=== Verse ${osisRef} ===`);
  console.log(`${verse.book} ${verse.chapter}:${verse.verse}`);
  console.log(verse.text);
  const footnotes = verse.footnotes || [];
  if (footnotes.length) {
    console.log(`Footnotes (${footnotes.length}):`);
    for (const fn of footnotes) {
      console.log(`  [${fn.marker || ""}] ${fn.note || fn.text || ""}`);
    }
  }
  const crossRefs = verse.crossReferences || [];
  if (crossRefs.length) {
    console.log(`Cross-references (${crossRefs.length}):`);
    for (const xr of crossRefs.slice(0, 5)) {
      console.log(`  -> ${xr.target} (${xr.source})`);
    }
    if (crossRefs.length > 5) console.log(`  ...and ${crossRefs.length - 5} more`);
  }
  console.log("");
}

async function showChapter(osis, chapter) {
  const data = await getJson(`/v1/chapter/${osis}/${chapter}`);
  const verses = data.verses || [];
  console.log(`=== ${osis} chapter ${chapter} (${verses.length} verses) ===`);
  for (const v of verses.slice(0, 3)) {
    console.log(`  ${v.verse}. ${v.text}`);
  }
  if (verses.length > 3) console.log(`  ...and ${verses.length - 3} more verses`);
  console.log("");
}

async function showPassage(ref) {
  const encoded = encodeURIComponent(ref);
  const data = await getJson(`/v1/passage/${encoded}`);
  const verses = data.verses || [];
  console.log(`=== Passage: ${ref} (${verses.length} verses) ===`);
  for (const v of verses) {
    console.log(`  ${v.bookOsis} ${v.chapter}:${v.verse} - ${v.text}`);
  }
  console.log("");
}

async function showCrossrefs(osisRef, source) {
  const params = source ? { source } : undefined;
  const data = await getJson(`/v1/crossrefs/${osisRef}`, params);
  const crossRefs = data.crossReferences || [];
  const entityLinks = data.entityLinks || [];
  const label = source ? `?source=${source}` : "(all sources)";
  console.log(`=== Cross-references for ${osisRef} ${label} ===`);
  console.log(`  crossReferences: ${crossRefs.length}`);
  console.log(`  entityLinks: ${entityLinks.length}`);
  for (const xr of crossRefs.slice(0, 5)) {
    console.log(`  -> ${xr.target} (${xr.source})`);
  }
  console.log("");
}

async function main() {
  console.log(`Using API base: ${apiBase}\n`);
  try {
    await showVerse("JHN.3.16");
    await showChapter("GEN", 1);
    await showPassage("John 3:16-18");
    await showCrossrefs("GEN.1.1", "tsk");
    await showCrossrefs("GEN.1.1");
  } catch (err) {
    console.error(`ERROR: ${err.message}`);
    if (typeof process !== "undefined") process.exitCode = 1;
  }
}

// Run when executed directly (Node.js), and expose for browser bundlers.
if (typeof require !== "undefined" && require.main === module) {
  main();
} else if (typeof window === "undefined") {
  main();
}

export { getJson, showVerse, showChapter, showPassage, showCrossrefs, main };
