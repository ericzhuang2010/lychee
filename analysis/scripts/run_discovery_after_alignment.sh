#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "${root}"

alignment_complete=results/audit/discovery_alignment_driver.complete
workflow_complete=results/audit/discovery_main_workflow.complete
log=analysis/logs/discovery_main_workflow.log
mkdir -p results/audit analysis/logs
exec > >(tee -a "${log}") 2>&1

while [[ ! -e ${alignment_complete} ]]; do
  echo "$(date --iso-8601=seconds) waiting for discovery alignment completion marker"
  sleep 60
done

while IFS=$'\t' read -r sample_id run _rest; do
  [[ ${sample_id} == sample_id ]] && continue
  bam=results/alignment/PRJNA830488/${sample_id}/Aligned.sortedByCoord.out.bam
  quant=results/quantification/PRJNA830488/salmon/${sample_id}/quant.sf
  meta=results/quantification/PRJNA830488/salmon/${sample_id}/aux_info/meta_info.json
  .conda/lychee-discovery/bin/samtools quickcheck -v "${bam}"
  test -s "${bam}.bai"
  test -s "${quant}"
  test -s "${meta}"
done < analysis/metadata/PRJNA830488_samples.tsv

sha256sum -c analysis/preregistration/external_validation_bundle.sha256
sha256sum -c analysis/preregistration/orthogonal_validation_bundle.sha256

echo "$(date --iso-8601=seconds) starting main discovery workflow"
.tools/bin/micromamba run -p .conda/lychee-discovery snakemake \
  --snakefile analysis/workflow/Snakefile \
  --configfile analysis/config/release.yaml \
  --cores 16 \
  --resources mem_mb=15000 alignment_slots=1 \
  --rerun-triggers mtime --printshellcmds

sha256sum -c results/discovery/frozen_results.sha256
test -s results/discovery/external_outcomes_unlock_timestamp.txt
touch "${workflow_complete}"
echo "$(date --iso-8601=seconds) main discovery workflow and freeze gate completed"
