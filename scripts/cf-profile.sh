#!/bin/sh
# On-demand Workers profile: https://blog.cloudflare.com/workers-on-demand-profiling/
# Usage: mise run profile [worker] [cpu|memory] [duration_ms]
# Writes profiles/<worker>-<type>-<YYYY-MM-DD>.pprof (pprof; open with `go tool pprof`
# or the dashboard). Needs cf >= 1.0.0-beta.13 (`cf workers versions profile`).
# Profiles the version that is serving 100% (or the largest share) of traffic
# unless CF_PROFILE_VERSION is set (a version UUID, 8+ char prefix, or "latest").
# Durable Object: set CF_PROFILE_DO_NAMESPACE and CF_PROFILE_DO_ACTOR.
# The profiler samples live isolates only. A Worker with no recent traffic
# returns "[10393] No recent executions"; that is expected on a quiet Worker.
set -eu
worker=${1:-${CF_PROFILE_WORKER:?usage: profile <worker> [cpu|memory] [duration_ms]}}
type=${2:-cpu}
duration=${3:-5000}
cf_bin=${CF_BIN:-cf}

case $type in
  cpu) api_type=cpu ;;
  memory | heap) api_type=heap; type=memory ;;
  *) echo "type must be cpu or memory (got: $type)" >&2; exit 2 ;;
esac
case $duration in
  '' | *[!0-9]*) echo "duration_ms must be an integer (got: $duration)" >&2; exit 2 ;;
esac

# cf caches under the nearest node_modules/.cache, else ./.cloudflare/cache (gitignored).
mkdir -p profiles .cloudflare/cache

version=${CF_PROFILE_VERSION:-}
if [ -z "$version" ]; then
  version=$($cf_bin -q workers deployments list --worker "$worker" --per-page 1 | node -e '
    let s = ""; process.stdin.on("data", (d) => (s += d)).on("end", () => {
      const d = JSON.parse(s); const dep = (d.deployments ?? d.result?.deployments ?? d)[0];
      const v = dep?.versions?.slice().sort((a, b) => b.percentage - a.percentage)[0];
      if (!v) process.exit(1); process.stdout.write(v.version_id);
    });')
fi

out="profiles/$worker-$type-$(date +%F).pprof"
set -- workers versions profile "$version" --worker-id "$worker" --duration-ms "$duration" --profile-type "$api_type"
if [ -n "${CF_PROFILE_DO_NAMESPACE:-}" ] || [ -n "${CF_PROFILE_DO_ACTOR:-}" ]; then
  set -- "$@" --namespace-id "${CF_PROFILE_DO_NAMESPACE:?set both CF_PROFILE_DO_NAMESPACE and CF_PROFILE_DO_ACTOR}" \
    --actor-id "${CF_PROFILE_DO_ACTOR:?set both CF_PROFILE_DO_NAMESPACE and CF_PROFILE_DO_ACTOR}"
fi

echo "profiling $worker@$version ($api_type, ${duration}ms) -> $out" >&2
if $cf_bin -q "$@" > "$out.tmp" && [ -s "$out.tmp" ]; then
  mv "$out.tmp" "$out"
  echo "$out" >&2
else
  rm -f "$out.tmp"
  echo "profile failed (see error above). Low-traffic Workers often have no live isolate to sample." >&2
  exit 1
fi
