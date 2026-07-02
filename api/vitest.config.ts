import { defineWorkersConfig } from "@cloudflare/vitest-pool-workers/config";
import { FIXTURES } from "./test/fixtures.mjs";

export default defineWorkersConfig({
  test: {
    poolOptions: {
      workers: {
        wrangler: { configPath: "./wrangler.toml" },
        miniflare: {
          // cacheWarn: false,
          // The R2 bucket binding. Seeded in beforeAll from SEED_FIXTURES.
          r2Buckets: ["BSB_DATASET"],
          bindings: {
            // Non-routable Arweave origin so tier 3 always fails fast during
            // tests (503 path) without hitting the network.
            ARWEAVE_ORIGIN: "https://bsb-arweave.invalid",
            WORKER_VERSION: "1.0.0",
            // JSON-serialized map of { R2Key: jsonString }. The test setup walks
            // this map and calls env.BSB_DATASET.put() for each entry inside
            // beforeAll. node:fs is unavailable inside workerd, so we carry the
            // fixtures in as a binding instead.
            SEED_FIXTURES: JSON.stringify(FIXTURES),
          },
        },
      },
    },
    // Run test files serially since we share a single seeded R2 bucket.
    fileParallelism: false,
    include: ["test/**/*.test.ts", "test/**/*.test.js"],
  },
});
