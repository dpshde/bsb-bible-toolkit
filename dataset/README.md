# BSB JSON Dataset

A free, structured, queryable JSON dataset built from the public-domain
**Berean Standard Bible (BSB)**. The dataset is served through a 4-tier
cache-aside API (Cloudflare edge cache, then R2, then Arweave, then 503) so
church apps, study tools, AI Scripture assistants, and reading-plan projects
can fetch verses, chapters, passages, footnotes, and cross-references over
HTTP with no API key, no rate limit, and permissive CORS.

The BSB text is public domain / CC0. The dataset code is MIT licensed. See the
[Licensing](#licensing) section for the cross-reference source attributions.

## Base URL

The Worker runs at the edge. Local development uses `wrangler dev` on port
8787; production is deployed to `bsb.workers.dev` initially.

```text
Local:   http://localhost:8787
Prod:    https://bsb-api.dpshade.workers.dev
Origin:  https://api_bsb.scripture.ar-io.dev   (Arweave permanent canonical copy, deferred)
```

All API paths are versioned under `/v1/` and are frozen forever. Schema
changes will go to `/v2/`.

## Endpoints

| Endpoint | Example | Returns |
|----------|---------|---------|
| `GET /v1/books` | `/v1/books` | Array of all 66 books with metadata |
| `GET /v1/book/:osis` | `/v1/book/GEN` | Full book JSON (all chapters + verses) |
| `GET /v1/chapter/:osis/:ch` | `/v1/chapter/GEN/1` | Full chapter with all verses |
| `GET /v1/verse/:osisRef` | `/v1/verse/GEN.1.1` | Single verse with footnotes, cross-refs, events |
| `GET /v1/passage/:ref` | `/v1/passage/John%203:16-18` | Parsed range expanded to individual verses |
| `GET /v1/resolve/:input` | `/v1/resolve/logosres:bible%2Bbsb.64.3.16` | Any input format resolved to canonical passage + verses |
| `GET /v1/search?q=...` | `/v1/search?q=beginning` | Verses whose text matches the query |
| `GET /v1/crossrefs/:osisRef` | `/v1/crossrefs/GEN.1.1` | Cross-references (with `?source=` filtering) |
| `GET /v1/health` | `/v1/health` | Service health, version, and cache tier status |

References may be OSIS (`GEN.1.1`, `JHN.3.16`) for `/v1/verse` and
`/v1/crossrefs`, or human-readable (`John 3:16-18`) for `/v1/passage`. The
`/v1/resolve/:input` endpoint accepts any format (see [Resolve endpoint](#resolve-endpoint)
below). Always URL-encode spaces as `%20`.

## JSON Schema

### Verse object

Every verse endpoint returns (or includes) a verse object with the fields
below. Empty arrays are always present, never `null` or omitted.

```json
{
  "ref": "GEN.1.1",
  "osis": "GEN.1.1",
  "osisRef": "GEN.1.1",
  "book": "Genesis",
  "bookOsis": "GEN",
  "chapter": 1,
  "verse": 1,
  "text": "In the beginning God created the heavens and the earth.",
  "footnotes": [],
  "crossReferences": [
    {
      "human": "Hebrews 11:1-3",
      "osis": "HEB.11.1-HEB.11.3",
      "source": "bsb-footnote",
      "target": "HEB.11.1-HEB.11.3"
    }
  ],
  "events": ["Creation of all things"],
  "entities": ["earth", "God"],
  "routeLink": "https://route.bible/gen.1.1",
  "translation": "BSB",
  "translationName": "Berean Standard Bible"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ref`, `osis`, `osisRef` | string | Canonical OSIS reference, `BOOK.CHAPTER.VERSE` (e.g. `GEN.1.1`) |
| `book` | string | Human-readable book name (`Genesis`) |
| `bookOsis` | string | OSIS book abbreviation (`GEN`, `PSA`, `JHN`, `REV`) |
| `chapter` | integer | Chapter number |
| `verse` | integer | Verse number |
| `text` | string | Verbatim BSB verse text (CC0) |
| `footnotes` | array | Footnote objects attached to this verse (may be empty) |
| `crossReferences` | array | BSB + TSK cross-references for this verse |
| `events` | array | Event labels from the enrichment JSONL (may be empty) |
| `entities` | array | Entity labels from the enrichment JSONL (may be empty) |
| `routeLink` | string | Lowercase route.bible deep link (`https://route.bible/gen.1.1`) |
| `translation` | string | Translation identifier (`BSB`) |
| `translationName` | string | Full translation name (`Berean Standard Bible`) |

### Footnote object

```json
{
  "marker": "a",
  "note": "Or 'When God began to create the heavens and the earth...'",
  "type": "explanation"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `marker` | string | Footnote marker letter/symbol from the USFM source |
| `note` | string | Footnote text content (USFM markers stripped) |
| `type` | string | Footnote category (`explanation`, `translation`, `alt`, etc.) |

### Cross-reference object

Each cross-reference carries a `source` field identifying its origin.

```json
{
  "target": "JHN.1.1",
  "osis": "JHN.1.1",
  "human": "John 1:1",
  "source": "tsk",
  "votes": 370
}
```

| Field | Type | Description |
|-------|------|-------------|
| `target` | string | Canonical OSIS target reference or range (`JHN.1.1`, `GEN.1.1-GEN.1.2`) |
| `osis` | string | OSIS form of the target (same as `target` for single-verse refs) |
| `human` | string | Human-readable target reference (e.g. `John 1:1`) |
| `source` | string | One of `bsb-footnote`, `tsk`, `acai`, `theographic` |
| `votes` | integer | TSK vote count (only present on `tsk` entries) |

### Book object

```json
{
  "osis": "GEN",
  "name": "Genesis",
  "chapters": [
    { "chapter": 1, "verses": [ /* verse objects */ ] }
  ]
}
```

### Chapter object

```json
{
  "chapter": 1,
  "verses": [ /* verse objects */ ]
}
```

### Cross-references response (`/v1/crossrefs/:osisRef`)

```json
{
  "ref": "GEN.1.1",
  "crossReferences": [
    { "target": "JHN.1.1", "source": "tsk", "votes": 370 }
  ],
  "entityLinks": [
    { "entity": "person:God", "type": "person", "source": "acai" }
  ]
}
```

## Resolve Endpoint

`GET /v1/resolve/:input` is the "inverted route.bible": pass it any Bible
reference format and it returns the canonical passage + verse text. It uses
`grab-bcv`'s `parseAnyPassage` to accept:

- **Human references**: `John 3:16`, `1 Cor 13:4-7`, `Genesis 1:1-2`
- **OSIS strings**: `JHN.3.16`, `GEN.1.1-GEN.1.2`, `jhn.3.16` (lowercase)
- **Book abbreviations**: `Jn 3:16`, `1co 13:4-7`
- **Bible app URIs**: `logosres:bible+bsb.64.3.16` (Logos), `accordance:bible:John 3:16`
- **Provider URLs**: `https://www.bible.com/bible/111/JHN.3.16`, `https://www.biblegateway.com/passage/?search=John+3:16`

The response uses the same verse-object schema as `/v1/passage`, plus two
fields that make the round-trip parsing transparent:

```json
{
  "originalInput": "john 3:16",
  "canonical": "JHN.3.16",
  "passage": "John 3:16",
  "ref": "JHN.3.16",
  "display": "John 3:16",
  "rangeType": "single",
  "start": { "book": "JHN", "chapter": 3, "verse": 16 },
  "end": { "book": "JHN", "chapter": 3, "verse": 16 },
  "verseCount": 1,
  "verses": [ /* full verse objects (same shape as /v1/passage) */ ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `originalInput` | string | The verbatim URL-decoded input the client submitted |
| `canonical` | string | Canonical OSIS reference (`JHN.3.16`, `GEN.1.1-2`) |
| `passage`, `display` | string | Human-readable display form (`John 3:16`) |
| `ref` | string | Same as `canonical` (alias for parity with `/v1/passage`) |
| `rangeType` | string | `single`, `same_chapter`, `chapter_range`, or `cross_reference` |
| `start`, `end` | object | `{ book, chapter, verse }` for the range bounds |
| `verseCount` | integer | Number of verse objects returned |
| `verses` | array | Full verse objects (identical schema to `/v1/passage`) |

### Resolve examples

```bash
# Human reference (single verse)
curl 'http://localhost:8787/v1/resolve/John%203:16'

# Human range with abbreviated book
curl 'http://localhost:8787/v1/resolve/1%20Cor%2013:4-7'

# OSIS string
curl 'http://localhost:8787/v1/resolve/JHN.3.16'

# Lowercase OSIS (route.bible canonical style)
curl 'http://localhost:8787/v1/resolve/jhn.3.16'

# Logos Bible app URI (book number maps via grab-bcv's Logos offset)
curl 'http://localhost:8787/v1/resolve/logosres:bible%2Bbsb.64.3.16'

# Accordance Bible app URI
curl 'http://localhost:8787/v1/resolve/accordance:bible:John%203:16'

# Bible.com URL (URL-encode the slashes)
curl 'http://localhost:8787/v1/resolve/https:%2F%2Fwww.bible.com%2Fbible%2F111%2FJHN.3.16'

# Bible Gateway URL
curl 'http://localhost:8787/v1/resolve/https:%2F%2Fwww.biblegateway.com%2Fpassage%2F%3Fsearch%3DJohn%2B3%3A16'
```

**Errors:**

- `400` - input could not be parsed as a Bible reference (e.g. `not-a-bible-reference`)
- `404` - input parsed but no verses were found in the dataset
- `503` - all cache tiers exhausted for the resolved verses

**Logos book numbering note:** grab-bcv 0.1.5 maps Logos book numbers using its
internal New Testament offset (NT starts at 61: Matt=61, Mark=62, Luke=63,
John=64). The `logosres:` scheme prefix is stripped by the Worker before
grab-bcv parses the reference. If a specific Logos resource uses a different
book numbering, the resolve endpoint returns a clean 400/404 rather than
fabricating a verse.

## Source Filtering

The `/v1/crossrefs/:osisRef` endpoint supports filtering by provenance via the
`?source=` query parameter. This is the recommended way to honor the different
licenses attached to each cross-reference source.

| `?source=` value | Source | License | Notes |
|------------------|--------|---------|-------|
| `bsb-footnote` | BSB USFM `\ref` tags | CC0 | 3,271 references from BSB footnotes |
| `tsk` | openbible.info TSK | CC-BY | ~344,800 reference pairs |
| `acai` | BibleAquifer ACAI entities | CC-BY-SA | ~113,022 entity links |
| `theographic` | Theographic mentions | CC-BY-SA | ~53,000 entity mentions |

### Filtering examples

```bash
# Only TSK cross-references (CC-BY)
curl 'http://localhost:8787/v1/crossrefs/GEN.1.1?source=tsk'

# Only BSB footnote cross-references (CC0)
curl 'http://localhost:8787/v1/crossrefs/GEN.1.1?source=bsb-footnote'

# Multiple sources (union of tsk + acai)
curl 'http://localhost:8787/v1/crossrefs/GEN.1.1?source=tsk&source=acai'

# No filter: return all sources
curl 'http://localhost:8787/v1/crossrefs/GEN.1.1'

# Invalid source values are silently ignored (return empty array, not an error)
curl 'http://localhost:8787/v1/crossrefs/GEN.1.1?source=invalid'
```

Source names are case-insensitive. Multiple `?source=` parameters are combined
as a union. Invalid source values are silently dropped, so a request containing
only invalid sources returns HTTP 200 with an empty `crossReferences` array.

## curl Examples

```bash
# Book catalog (66 books)
curl 'http://localhost:8787/v1/books'

# Full book JSON
curl 'http://localhost:8787/v1/book/GEN'

# Full chapter
curl 'http://localhost:8787/v1/chapter/GEN/1'

# Single verse with footnotes, cross-references, events, and entities
curl 'http://localhost:8787/v1/verse/GEN.1.1'

# Parsed human-readable passage (URL-encode spaces and colons)
curl 'http://localhost:8787/v1/passage/John%203:16-18'

# Resolve any input format (human, OSIS, URI, URL) to canonical passage + verses
curl 'http://localhost:8787/v1/resolve/John%203:16'
curl 'http://localhost:8787/v1/resolve/logosres:bible%2Bbsb.64.3.16'

# Verse search across the whole Bible
curl 'http://localhost:8787/v1/search?q=beginning'

# Cross-references for a verse (all sources)
curl 'http://localhost:8787/v1/crossrefs/GEN.1.1'

# Cross-references filtered to a single source
curl 'http://localhost:8787/v1/crossrefs/GEN.1.1?source=tsk'

# Service health and cache tier status
curl 'http://localhost:8787/v1/health'
```

Every response includes CORS headers
(`Access-Control-Allow-Origin: *`), `Content-Type: application/json`, and an
`X-Origin` header indicating which cache tier served the request
(`edge`, `r2`, or `arweave`). Verse, chapter, book, and passage responses are
cached with `Cache-Control: public, max-age=31536000, immutable`.

## Python Quickstart

Fetch a verse and print its text using `requests` (or the standard library
`urllib.request`):

```python
import requests

response = requests.get("https://bsb.workers.dev/v1/verse/JHN.3.16", timeout=10)
response.raise_for_status()
verse = response.json()
print(f"{verse['book']} {verse['chapter']}:{verse['verse']}")
print(verse["text"])
```

For a runnable example, see
[`dataset/examples/python_quickstart.py`](examples/python_quickstart.py). For a
365-day reading plan generator, see
[`dataset/examples/reading_plan.py`](examples/reading_plan.py).

## JavaScript Quickstart

Call the API from a browser, Node.js 18+, or any `fetch`-compatible runtime:

```javascript
async function fetchVerse(osisRef) {
  const response = await fetch(`https://bsb.workers.dev/v1/verse/${osisRef}`);
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

const verse = await fetchVerse("JHN.3.16");
console.log(`${verse.book} ${verse.chapter}:${verse.verse}`);
console.log(verse.text);
```

For a runnable browser example, see
[`dataset/examples/javascript_fetch.js`](examples/javascript_fetch.js).

## OSIS Reference Format

The dataset uses the SBL OSIS abbreviation scheme for book codes:

| OSIS | Book | OSIS | Book | OSIS | Book |
|------|------|------|------|------|------|
| `GEN` | Genesis | `PSA` | Psalms | `MAT` | Matthew |
| `EXO` | Exodus | `PRO` | Proverbs | `MRK` | Mark |
| `LEV` | Leviticus | `ECC` | Ecclesiastes | `LUK` | Luke |
| `NUM` | Numbers | `SNG` | Song of Solomon | `JHN` | John |
| `DEU` | Deuteronomy | `ISA` | Isaiah | `ACT` | Acts |
| `JOS` | Joshua | `JER` | Jeremiah | `ROM` | Romans |
| `JDG` | Judges | `EZK` | Ezekiel | `1CO` | 1 Corinthians |
| `RUT` | Ruth | `DAN` | Daniel | `2CO` | 2 Corinthians |
| `1SA` | 1 Samuel | `HOS` | Hosea | `GAL` | Galatians |
| `2SA` | 2 Samuel | `JOL` | Joel | `EPH` | Ephesians |
| `1KI` | 1 Kings | `AMO` | Amos | `PHP` | Philippians |
| `2KI` | 2 Kings | `OBA` | Obadiah | `COL` | Colossians |
| `1CH` | 1 Chronicles | `JON` | Jonah | `1TH` | 1 Thessalonians |
| `2CH` | 2 Chronicles | `MIC` | Micah | `2TH` | 2 Thessalonians |
| `EZR` | Ezra | `NAM` | Nahum | `1TI` | 1 Timothy |
| `NEH` | Nehemiah | `HAB` | Habakkuk | `2TI` | 2 Timothy |
| `EST` | Esther | `ZEP` | Zephaniah | `TIT` | Titus |
| `JOB` | Job | `HAG` | Haggai | `PHM` | Philemon |
| `MAL` | Malachi | `HEB` | Hebrews | `JAS` | James |
| `1PE` | 1 Peter | `2PE` | 2 Peter | `1JN` | 1 John |
| `2JN` | 2 John | `3JN` | 3 John | `JUD` | Jude |
| `REV` | Revelation | | | | |

Verse references use dot separators: `BOOK.CHAPTER.VERSE` (e.g. `JHN.3.16`).
Ranges use a hyphen: `GEN.1.1-GEN.1.2`. route.bible deep links use the same
form, lowercased (`https://route.bible/jhn.3.16`).

## Output Files

The dataset builder writes the following files under `output/dataset/`. They
are gitignored (run the builder locally or in CI to regenerate them) and
uploaded to Arweave + R2 at deploy time.

| File | Description |
|------|-------------|
| `bsb-dataset.json` | Unified dataset (~22 MB) with all 66 books, chapters, and verses |
| `manifest.json` | Book list, verse counts, source versions, and build hash |
| `cross-refs.json` | Aggregated cross-reference index (CC0 + CC-BY sources only) |
| `entity-links.json` | ACAI + Theographic entity links (CC-BY-SA, isolated for licensing) |
| `books/<OSIS>.json` | Per-book JSON file (66 files) |
| `books/<OSIS>/chapters/<N>.json` | Per-chapter JSON files (1,189 files) |
| `books/<OSIS>/verses/<OSIS>.<C>.<V>.json` | Per-verse JSON files (31,086 files) |

## Licensing

| Component | License | Attribution |
|-----------|---------|-------------|
| BSB Bible text | CC0 / Public Domain | Berean Bible Translation Committee |
| BSB USFM `\ref` cross-references | CC0 | Berean Bible |
| openbible.info TSK cross-references | CC-BY | "Cross references from OpenBible.info" |
| BibleAquifer ACAI entity links | CC-BY-SA 4.0 | BibleAquifer/ACAI |
| Theographic Bible metadata | CC-BY-SA 4.0 | theographic-bible-metadata |
| Toolkit source code | MIT | This repository |

To respect the license mix, CC-BY-SA data (ACAI, Theographic) is kept in a
separate `entity-links.json` file and is never merged into the main
`cross-refs.json`. Use the `?source=` filter to fetch only the sources your
project's license allows.

## See Also

- [Main README](../README.md) - project overview and PDF/EPUB tooling
- [Build pipeline](../src/bsb_pdf_toolkit/build_dataset.py) - Python dataset builder
- [Worker source](../api/worker.js) - Cloudflare Worker (4-tier cache-aside)
- [Deployment workflow](../.github/workflows/deploy_api.yml) - CI pipeline
