// Bible reference parsing and range expansion.
// All parsing is delegated to `grab-bcv` (MANDATORY per mission directives).
// No custom Bible reference parsing code lives here.

import {
  tryParsePassage,
  formatPassageForDisplay,
  getVerseCount,
  OSIS_BOOK_ORDER,
  OSIS_BOOK_CODES,
  OSIS_BOOK_NAMES,
} from "grab-bcv";

// Compare two OSIS book codes by canonical Protestant order.
export function compareOsisBooks(a, b) {
  const ai = OSIS_BOOK_ORDER.get(a);
  const bi = OSIS_BOOK_ORDER.get(b);
  if (ai === undefined || bi === undefined) return a.localeCompare(b);
  return ai - bi;
}

// Expand a ParsedPassage (start..end) into an ordered list of OSIS verse refs
// of the form BOOK.CHAPTER.VERSE. Handles single verses, same-chapter ranges,
// full-chapter ranges, cross-chapter ranges, and cross-book ranges.
//
// Returns { ok: true, refs: string[], display: string } on success, or
// { ok: false, error: string } if the passage cannot be expanded.
export function expandPassageToVerseRefs(parsed) {
  const start = parsed.start;
  const end = parsed.end;

  // For a single verse (start === end), short-circuit.
  if (
    start.book === end.book &&
    start.chapter === end.chapter &&
    (start.verse ?? 1) === (end.verse ?? 1)
  ) {
    const ref = `${start.book}.${start.chapter}.${start.verse ?? 1}`;
    return { ok: true, refs: [ref], display: formatPassageForDisplay(parsed) };
  }

  const refs = [];

  // Walk books from start.book to end.book in canonical order.
  const orderedBooks = OSIS_BOOK_CODES.filter((code) => {
    const order = OSIS_BOOK_ORDER.get(code);
    const so = OSIS_BOOK_ORDER.get(start.book);
    const eo = OSIS_BOOK_ORDER.get(end.book);
    return order >= so && order <= eo;
  });

  for (const book of orderedBooks) {
    const isStartBook = book === start.book;
    const isEndBook = book === end.book;

    let firstChapter, lastChapter;
    if (isStartBook && isEndBook) {
      firstChapter = start.chapter;
      lastChapter = end.chapter;
    } else if (isStartBook) {
      firstChapter = start.chapter;
      lastChapter = maxChapter(book);
    } else if (isEndBook) {
      firstChapter = 1;
      lastChapter = end.chapter;
    } else {
      firstChapter = 1;
      lastChapter = maxChapter(book);
    }

    for (let ch = firstChapter; ch <= lastChapter; ch++) {
      const total = getVerseCount(book, ch);
      if (!total) continue;

      let firstVerse, lastVerse;
      if (isStartBook && ch === start.chapter) firstVerse = start.verse ?? 1;
      else firstVerse = 1;

      if (isEndBook && ch === end.chapter) lastVerse = end.verse ?? total;
      else lastVerse = total;

      for (let v = firstVerse; v <= lastVerse; v++) {
        refs.push(`${book}.${ch}.${v}`);
      }
    }
  }

  return { ok: true, refs, display: formatPassageForDisplay(parsed) };
}

// Helper: best-effort max chapter for a book.
function maxChapter(book) {
  let max = 0;
  for (const code of OSIS_BOOK_CODES) {
    if (code === book) {
      // Brute force verse count lookup: find largest chapter with verse data.
      for (let ch = 200; ch >= 1; ch--) {
        if (getVerseCount(book, ch)) return ch;
      }
    }
  }
  return max;
}

// Parse a passage string from the URL path. Returns:
//   { ok: true, parsed, refs, display }
//   { ok: false, status: 400|404, error: string }
export function parsePassageInput(raw) {
  // grab-bcv's tryParsePassage distinguishes EMPTY (whitespace/empty -> 400)
  // from INVALID_FORMAT / INVALID_BOOK / REVERSED_RANGE (-> 404).
  const result = tryParsePassage(raw);
  if (!result.ok) {
    const code = result.error.code;
    if (code === "EMPTY") return { ok: false, status: 400, error: "Passage reference is empty." };
    if (code === "INVALID_BOOK") return { ok: false, status: 404, error: `Unknown book in reference: "${raw}".` };
    // INVALID_FORMAT, INVALID_NUMBER, REVERSED_RANGE
    return {
      ok: false,
      status: 404,
      error: result.error.message || `Could not parse reference: "${raw}".`,
    };
  }

  const expanded = expandPassageToVerseRefs(result.value);
  if (!expanded.ok) {
    return { ok: false, status: 404, error: expanded.error || `Could not expand reference: "${raw}".` };
  }
  return {
    ok: true,
    parsed: result.value,
    refs: expanded.refs,
    display: expanded.display,
  };
}

export { OSIS_BOOK_ORDER, OSIS_BOOK_CODES, OSIS_BOOK_NAMES };
