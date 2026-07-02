# Why BSB API?

A comparison of Bible API options for builders who need Scripture text in their
apps, tools, and projects.

## TL;DR

| Feature | BSB API | bible.helloao.org | API.Bible |
|---|---|---|---|
| **Cost** | Free forever | Free | Free tier (5K calls/mo), $29+/mo for Pro |
| **API key required** | No | No | Yes |
| **Rate limits** | None (100K/day Cloudflare free tier) | None stated | 5K/mo free, 150K/mo paid |
| **Commercial use** | Yes (CC0 text) | Yes | Restricted on free tier; paid per-Bible licensing |
| **Translation** | Berean Standard Bible (public domain) | 1000+ translations | Many translations (mostly copyrighted) |
| **Latency** | Edge-cached globally (Cloudflare) | AWS single-region | Centralized API server |
| **Cross-references** | Yes (TSK, ACAI, Theographic, BSB footnotes) | No | No |
| **Entity/event enrichment** | Yes | No | No |
| **Reference parsing** | OSIS, human refs, Bible app URIs (Logos, Accordance), provider URLs | No | No |
| **Search** | Yes | No | Yes (paid plans) |
| **Footnotes** | Yes | Yes | Varies by translation |
| **Permanent/archival copy** | Planned: Arweave via ArNS | No | No |
| **Self-hostable** | Yes (open source, R2 + Worker) | No | No |
| **Schema stability** | `/v1/` frozen forever | Undocumented | Undocumented |

## BSB API

**Best for:** Builders who want a fast, free, enrichment-rich API for the
public-domain Berean Standard Bible with no API key, no rate limit headaches,
and cross-references included.

- **URL:** `https://bsb-api.dpshade.workers.dev`
- **Docs:** [dataset/README.md](README.md)
- **Source:** Open source Worker + dataset builder
- **Text license:** CC0 / public domain

### Unique strengths

1. **Enrichment data no one else has.** Every verse ships with cross-references
   from four sources (BSB footnotes, TSK, ACAI, Theographic), plus named
   entities (people, places, things) and event labels. Helloao and API.Bible
   return verse text only.

2. **Multi-format reference resolution.** The `/v1/resolve/:input` endpoint
   accepts anything -- `John 3:16`, `JHN.3.16`, `accordance:bible:John 3:16`,
   `logosres:bible+bsb.64.3.16`, `https://www.bible.com/bible/111/JHN.3.16` --
   and returns the canonical passage. No other Bible API does this.

3. **Edge-cached globally.** Runs on Cloudflare Workers with a 4-tier
   cache-aside strategy (edge cache, R2, Arweave, 503). Verse responses include
   `Cache-Control: public, max-age=31536000, immutable` so CDN edges worldwide
   serve subsequent requests with near-zero latency.

4. **No strings attached.** No API key, no signup, no terms of service to
   accept, no commercial restrictions. The BSB text is CC0. The code is MIT.
   Copy it, fork it, self-host it.

5. **Permanent archival planned.** The dataset will have an Arweave permanent
   copy via ArNS (`api_bsb.scripture.ar-io.dev`) so the API remains accessible
   even if Cloudflare disappears.

### Limitations

- **One translation only.** The BSB is a single, modern, public-domain
  translation. If you need NIV, ESV, NASB, or other copyrighted translations,
  use API.Bible (and pay licensing fees).
- **English only.** The BSB is an English translation.

---

## bible.helloao.org

**Best for:** Builders who need many translations and are okay with an
undocumented API from a small team.

- **URL:** `https://bible.helloao.org`
- **Docs:** Minimal landing page, no API reference

### Strengths

- 1000+ translations in one API
- No API key, no rate limits, no copyright restrictions
- Free

### Why you might choose BSB API instead

- **No enrichment.** Helloao returns verse text and footnotes. No
  cross-references, no entity links, no events. If you need study data, you
  would have to source and integrate it separately.
- **No reference parsing.** You need to know the translation ID, book ID, and
  chapter/verse numbers to construct requests. BSB API accepts human refs, OSIS,
  and Bible app URIs.
- **No search.** Helloao has no text search endpoint.
- **Single-region hosting.** Helloao runs on AWS in one region. BSB API runs on
  Cloudflare's global edge network (300+ locations).
- **Undocumented.** No formal API contract, no versioned schema, no guarantee of
  stability.
- **No permanent copy.** If Helloao goes down, the API disappears.

---

## API.Bible

**Best for:** Commercial apps that need copyrighted translations (NIV, ESV,
NASB, NLT, etc.) and can afford per-translation licensing fees.

- **URL:** `https://api.bible`
- **Docs:** [api.bible](https://api.bible/)

### Strengths

- Many copyrighted translations from major publishers
- Unified format across translations
- Search functionality (paid plans)
- Backed by the American Bible Society

### Why you might choose BSB API instead

- **Cost.** API.Bible's free tier is 5K calls/month, non-commercial only. The
  Pro plan is $29+/month with 150K calls. Commercial use requires per-Bible
  licensing ($10-$250/month per translation based on user count). BSB API is
  free with no limits.
- **API key required.** Every request needs a key, which means signup,
  management, and rotation. BSB API has no keys.
- **No enrichment.** API.Bible returns verse text and footnotes. No
  cross-references, no entity data, no events.
- **Centralized.** Requests hit a single API server, not a global edge network.
- **Commercial restrictions.** The free tier explicitly prohibits ads, fees,
  freemium models, or upsells. The BSB text is CC0 -- do anything you want.
- **Closed source.** You depend on API.Bible's infrastructure and availability.

---

## Decision guide

| If you need... | Use |
|---|---|
| Public-domain English Bible with cross-refs and entities | **BSB API** |
| Fast, keyless, globally cached verse lookups | **BSB API** |
| Self-hostable Bible API you control | **BSB API** |
| Reference resolution from Bible app URIs (Logos, Accordance) | **BSB API** |
| Many translations, no enrichment needed | **Helloao** |
| Copyrighted translations (NIV, ESV, NASB) for a commercial app | **API.Bible** |
| Text search across copyrighted translations | **API.Bible** (paid) |
