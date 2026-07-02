// Multi-format Bible reference resolution for the /v1/resolve endpoint.
//
// The resolve endpoint is the "inverted route.bible": it accepts ANY input
// format (human refs, OSIS strings, Bible app URIs, provider URLs) and
// returns the canonical passage + verse text. All parsing is delegated to
// `grab-bcv` (MANDATORY per mission directives). No custom Bible reference
// parsing code lives here; this module only normalizes URI scheme prefixes
// that grab-bcv's `tryParseAnyPassage` does not route on its own, then hands
// the cleaned input to grab-bcv.
//
// Supported input formats (all handled by grab-bcv's parseAnyPassage):
//   - Human references: "John 3:16", "1 Cor 13:4-7", "Genesis 1:1-2"
//   - OSIS strings: "JHN.3.16", "GEN.1.1-GEN.1.2", "jhn.3.16"
//   - Book abbreviations: "Jn 3:16", "1co 13:4-7"
//   - Bible.com URLs: "https://www.bible.com/bible/111/JHN.3.16"
//   - Bible Gateway URLs: "https://www.biblegateway.com/passage/?search=John+3:16"
//   - Accordance URIs: "accordance:bible:John 3:16"
//   - Logos URIs: "logosres:bible+bsb.64.3.16" (see normalizeLogosresInput)

import { tryParseAnyPassage } from "grab-bcv";
import { expandPassageToVerseRefs } from "./passage.js";

// grab-bcv's parseAnyPassage handles Accordance URIs, Bible.com URLs, Bible
// Gateway URLs, OSIS strings, human refs, and book abbreviations directly.
// However, it does not strip the `logosres:` URI scheme prefix before running
// its internal Logos reference parser (which expects the bare
// `bible+<resource>.<book>.<chapter>.<verse>` form). normalizeLogosresInput
// performs that minimal scheme-prefix strip so grab-bcv's own Logos parser can
// handle the reference. This is URI normalization only; grab-bcv still owns
// the book-number-to-OSIS mapping and all reference validation.
//
// Known limitation (documented per VAL-RESOLVE cross-cutting notes): grab-bcv
// 0.1.5 maps Logos book numbers using its own internal NT offset (NT starts at
// 61: Matt=61, Mark=62, Luke=63, John=64). Some Logos resources use different
// book numberings. If a specific resource's numbering diverges from
// grab-bcv's mapping, the resolve endpoint returns a clean 400/404 rather than
// fabricating a verse.
function normalizeLogosresInput(input) {
  if (typeof input !== "string") return input;
  const match = input.match(/^logosres:(.+)$/i);
  return match ? match[1] : input;
}

// Parse any input format for the /v1/resolve endpoint. Returns:
//   { ok: true, parsed, refs, canonical, display }
//   { ok: false, status: 400|404, error: string }
//
// - Empty/whitespace input -> 400 (VAL-RESOLVE-017 distinguishes this from
//   unparseable non-empty input, which is also 400 per the contract).
// - grab-bcv INVALID_FORMAT / INVALID_BOOK on non-empty input -> 400
//   (VAL-RESOLVE-017: "400 for unparseable input").
// - A parseable reference whose book is not in the BSB canon (e.g. "1 Nephi
//   3:7") is rejected by grab-bcv as INVALID_FORMAT/INVALID_BOOK -> 400. The
//   contract notes this may surface as 400 when grab-bcv does not recognize
//   the book at all.
export function parseResolveInput(rawInput) {
  const raw = typeof rawInput === "string" ? rawInput : "";
  if (raw.trim() === "") {
    return { ok: false, status: 400, error: "Resolve input is empty." };
  }

  // Minimal URI normalization for the logosres: scheme, then hand off to
  // grab-bcv's multi-format parser.
  const normalized = normalizeLogosresInput(raw);
  const result = tryParseAnyPassage(normalized);
  if (!result.ok) {
    const code = result.error.code;
    if (code === "EMPTY") {
      return { ok: false, status: 400, error: "Resolve input is empty." };
    }
    // INVALID_FORMAT, INVALID_BOOK, INVALID_NUMBER, REVERSED_RANGE: all
    // surface as 400 per VAL-RESOLVE-017 ("400 for unparseable input").
    return {
      ok: false,
      status: 400,
      error: `Could not parse input: "${raw}".`,
    };
  }

  const parsed = result.value;
  const expanded = expandPassageToVerseRefs(parsed);
  if (!expanded.ok) {
    return {
      ok: false,
      status: 400,
      error: expanded.error || `Could not expand reference: "${raw}".`,
    };
  }

  return {
    ok: true,
    parsed,
    refs: expanded.refs,
    canonical: parsed.canonical,
    display: expanded.display,
  };
}
