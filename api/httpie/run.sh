#!/usr/bin/env bash
# BSB API HTTPie collection runner.
# Usage:
#   ./httpie/run.sh <request-name> [example-index]
#   ./httpie/run.sh health
#   ./httpie/run.sh verse 0
#   ./httpie/run.sh resolve 3
#
# Start the dev server first:  cd api && npm run dev
# Override the host with BSB_API_BASE, e.g.:
#   BSB_API_BASE=https://my-worker.workers.dev ./httpie/run.sh health

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
BASE="${BSB_API_BASE:-http://localhost:8787}"

# name | method | path-template | example-1 | example-2 | ...
requests() {
  case "$1" in
    health)     echo "GET /v1/health" ;;
    books)      echo "GET /v1/books" ;;
    book)       echo "GET /v1/book/JHN|GET /v1/book/GEN|GET /v1/book/1CO|GET /v1/book/PSA" ;;
    chapter)    echo "GET /v1/chapter/JHN/3|GET /v1/chapter/GEN/1|GET /v1/chapter/PSA/23" ;;
    verse)      echo "GET /v1/verse/JHN.3.16|GET /v1/verse/GEN.1.1|GET /v1/verse/1CO.13.4" ;;
    passage)    echo "GET /v1/passage/John%203:16|GET /v1/passage/1%20Cor%2013:4-7|GET /v1/passage/GEN.1.1-GEN.1.2" ;;
    resolve)    echo "GET /v1/resolve/John%203:16|GET /v1/resolve/JHN.3.16|GET /v1/resolve/accordance:bible:John%203:16|GET /v1/resolve/bible+bsb.64.3.16" ;;
    search)     echo "GET /v1/search?q=love|GET /v1/search?q=light%20of%20the%20world|GET /v1/search?q=Genesis" ;;
    crossrefs)  echo "GET /v1/crossrefs/JHN.3.16|GET /v1/crossrefs/JHN.3.16?source=tsk|GET /v1/crossrefs/GEN.1.1?source=tsk&source=acai" ;;
    *) echo "ERROR: Unknown request '$1'"; echo "Available: health books book chapter verse passage resolve search crossrefs"; exit 1 ;;
  esac
}

if [ $# -lt 1 ]; then
  echo "Usage: $0 <request-name> [example-index]"
  echo ""
  echo "Available requests:"
  for r in health books book chapter verse passage resolve search crossrefs; do
    desc=$(head -1 "$DIR/requests/$r.http" 2>/dev/null | sed 's/^# //')
    printf "  %-12s %s\n" "$r" "$desc"
  done
  exit 0
fi

NAME="$1"
IDX="${2:-0}"

RAW=$(requests "$NAME")
if [[ "$RAW" == ERROR:* ]]; then
  echo "$RAW"
  exit 1
fi

IFS='|' read -ra EXS <<< "$RAW"
if [ "$IDX" -ge "${#EXS[@]}" ]; then
  echo "Example index $IDX out of range (0-$((${#EXS[@]} - 1)))"
  exit 1
fi

SEL="${EXS[$IDX]}"
METHOD=$(echo "$SEL" | awk '{print $1}')
PATH_Q=$(echo "$SEL" | awk '{print $2}')

URL="${BASE}${PATH_Q}"

echo "→ ${METHOD} ${URL}"
echo ""
exec http --pretty=format "${URL}"
