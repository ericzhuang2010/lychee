#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "${root}"

mkdir -p results/audit
exec 9>results/audit/discovery_alignment_driver.lock
if ! flock -n 9; then
  echo "another discovery alignment driver holds the lock" >&2
  exit 1
fi

raw_dir=data/active_discovery/PRJNA830488/fastq
salmon_dir=results/quantification/PRJNA830488/salmon
runner=analysis/scripts/run_discovery_sample.sh
micromamba=.tools/bin/micromamba
environment=.conda/lychee-discovery

wait_for_completed_quantification() {
  local sample_id=$1
  while [[ ! -s ${salmon_dir}/${sample_id}/quant.sf || \
           ! -s ${salmon_dir}/${sample_id}/aux_info/meta_info.json ]]; do
    echo "waiting for completed quantification: ${sample_id}"
    sleep 30
  done
  while pgrep -x salmon >/dev/null; do
    echo "waiting for Salmon process to exit: ${sample_id}"
    sleep 15
  done
}

wait_for_validated_fastq_pair() {
  local run_accession=$1
  local r1=${raw_dir}/${run_accession}_1.fastq.gz
  local r2=${raw_dir}/${run_accession}_2.fastq.gz
  while true; do
    if [[ -s ${r1} && -s ${r2} && ! -e ${r1}.aria2 && ! -e ${r2}.aria2 ]] && \
       gzip -t "${r1}" "${r2}"; then
      return 0
    fi
    echo "waiting for validated FASTQ pair: ${run_accession}"
    sleep 30
  done
}

wait_for_completed_quantification GW_P2

samples=(
  "GW_P3 SRR18856607"
  "GW_M1 SRR18856600"
  "GW_M2 SRR18856599"
  "GW_M3 SRR18856598"
  "YR_P1 SRR18856603"
  "YR_P2 SRR18856602"
  "YR_P3 SRR18856601"
  "YR_M1 SRR18856606"
  "YR_M2 SRR18856605"
  "YR_M3 SRR18856604"
)

for specification in "${samples[@]}"; do
  read -r sample_id run_accession <<<"${specification}"
  wait_for_validated_fastq_pair "${run_accession}"
  echo "starting serial discovery sample: ${sample_id} ${run_accession}"
  "${micromamba}" run -p "${environment}" "${runner}" "${sample_id}" "${run_accession}"
  wait_for_completed_quantification "${sample_id}"
done

touch results/audit/discovery_alignment_driver.complete
echo "all serial discovery samples completed"
