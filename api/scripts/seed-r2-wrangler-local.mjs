#!/usr/bin/env node
// Seeds the local Miniflare R2 bucket used by `wrangler dev` with a focused
// subset of JSON keys that the curl smoke tests exercise. Uses
// `wrangler r2 object put --local` so writes go to the local persistence
// directory that wrangler dev reads from.
//
// This is a dev/test affordance. The full dataset (~62k files) is seeded at
// deploy time by the CI workflow (M3) using bulk wrangler commands.
//
// Usage: cd api && node scripts/seed-r2-wrangler-local.mjs

import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = resolve(fileURLToPath(import.meta.url), "..");
const REPO_API = resolve(__dirname, "..");
const SEED_DIR = join(REPO_API, "seed-data");

if (!existsSync(SEED_DIR)) {
  console.error(`seed-data/ not found at ${SEED_DIR}.`);
  console.error("Run: node scripts/seed-r2-local.mjs");
  process.exit(1);
}

// R2 keys we need for the curl smoke tests. Kept small so seeding finishes
// quickly; this is a dev affordance, not a full dataset seed.
function listKeys() {
  const keys = new Set([
    "v1/books.json",
    "v1/search-index.json",
    "v1/book/GEN.json",
    "v1/chapter/GEN/1.json",
    "v1/verse/GEN.1.1.json",
    "v1/verse/GEN.1.2.json",
    "v1/crossrefs/GEN.1.1.json",
    "v1/verse/MRK.1.1.json",
    "v1/verse/MAT.1.1.json",
  ]);

  // John 3:16-18 and John 3:16-John 4:2 (JHN.3.16..36 + JHN.4.1..2)
  for (let v = 16; v <= 36; v++) keys.add(`v1/verse/JHN.3.${v}.json`);
  keys.add("v1/verse/JHN.4.1.json");
  keys.add("v1/verse/JHN.4.2.json");

  // Psalm 119:1-3
  for (let v = 1; v <= 3; v++) keys.add(`v1/verse/PSA.119.${v}.json`);

  return [...keys];
}

function put(key) {
  const file = join(SEED_DIR, key);
  if (!existsSync(file)) return false;
  try {
    execFileSync(
      "npx",
      [
        "wrangler",
        "r2",
        "object",
        "put",
        `bsb-dataset/${key}`,
        `--file=${file}`,
        "--local",
        "--content-type=application/json",
      ],
      { cwd: REPO_API, stdio: "ignore", timeout: 15000 },
    );
    return true;
  } catch {
    return false;
  }
}

async function main() {
  console.log("Seeding local R2 bucket (subset for curl smoke tests)...");
  const keys = listKeys();
  const CONCURRENCY = 8;
  let ok = 0;
  let fail = 0;
  const failures = [];

  async function worker(queue) {
    while (queue.length) {
      const k = queue.shift();
      const success = put(k);
      if (success) ok++;
      else {
        fail++;
        failures.push(k);
      }
    }
  }

  const queue = [...keys];
  const workers = Array.from({ length: CONCURRENCY }, () => worker(queue));
  await Promise.all(workers);

  if (failures.length > 0) {
    console.warn(`  failed (${failures.length}): ${failures.slice(0, 5).join(", ")}`);
  }
  console.log(`Seeded ${ok} keys (${fail} failures).`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
