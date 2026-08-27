#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "${root}"

lock=results/audit/discovery_alignment_driver.lock
complete=results/audit/discovery_alignment_driver.complete
driver=analysis/scripts/run_remaining_discovery_samples.sh
max_restarts=${1:-3}
restarts=0

mkdir -p results/audit
while [[ ! -e ${complete} ]]; do
  if flock -n "${lock}" true; then
    ((restarts += 1))
    if ((restarts > max_restarts)); then
      echo "$(date --iso-8601=seconds) discovery driver exceeded ${max_restarts} restart attempts" >&2
      exit 1
    fi
    echo "$(date --iso-8601=seconds) restarting checkpoint-aware discovery driver (attempt ${restarts}/${max_restarts})"
    if bash "${driver}"; then
      continue
    fi
    echo "$(date --iso-8601=seconds) discovery driver exited nonzero; retrying after 60 seconds" >&2
  else
    echo "$(date --iso-8601=seconds) discovery driver is active; supervisor is standing by"
  fi
  sleep 60
done

echo "$(date --iso-8601=seconds) discovery alignment completion marker observed"
